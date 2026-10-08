"""Rencontres aléatoires des jeux de la 2e génération, lues dans pret (pret_gen2_wild.py) et rattachées aux zones
PokéAPI de leurs cartes (tools/data/map_areas.csv).

PokéAPI décrit mal ces rencontres pour Or et Argent (moments de la journée perdus dans les grottes et dans Argent,
emplacements d'essaim manquants, Concours de capture absent) : ses rencontres de ces méthodes sont écartées et
remplacées par les tables du jeu. Chaque carte affichée qui a des rencontres aléatoires a une seule zone ; deux
cartes d'une même zone doivent avoir les mêmes tables (les cinq parties du rez-de-chaussée des Tourb'Îles). Une
carte jamais affichée (carte de test) est ignorée, comme dans les cartes générées.

Les combats scriptés à objet forcé ou chromatiques (pret_gen2_wild.special_battles) deviennent une note sur la
rencontre fixe correspondante : l'objet tenu des Pokémon sauvages (pokemon_item) vaut pour l'espèce, pas pour eux.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .games import Game
from .maps import read_map_areas
from .pret_gen2_wild import SpecialBattle, WildTable, special_battles, wild_tables
from .pret_identifiers import item_identifier, species_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Méthodes PokéAPI remplacées par les tables pret. PokéAPI répartit Coup d'Boule en trois méthodes selon l'arbre
# (taux bas et normal : table commune, taux élevé : table rare) ; pret les ramène à deux tables (headbutt et
# headbutt-high).
REPLACED_METHODS = frozenset(
    {
        "walk",
        "surf",
        "old-rod",
        "good-rod",
        "super-rod",
        "headbutt-low",
        "headbutt-normal",
        "headbutt-high",
        "rock-smash",
    }
)
_NO_ITEM = "NO_ITEM"


@dataclass(frozen=True)
class WildEncounter:
    """Un emplacement d'une table pret, avec les identifiants de la base."""

    version_id: int
    area_id: int
    species_id: int
    method_id: int
    conditions: tuple[int, ...]
    min_level: int
    max_level: int
    chance: int


@dataclass(frozen=True)
class BattleNote:
    """Note d'une rencontre fixe : la version, les zones de la carte du combat et le Pokémon combattu."""

    version_ids: frozenset[int]
    area_ids: frozenset[int]
    species_id: int
    note: str


def gen2_wild_encounters(builder: DatabaseBuilder, game: Game) -> list[WildEncounter]:
    """Rencontres aléatoires du jeu, version par version."""
    repo = builder.gen2_repo(game, "les rencontres aléatoires")
    areas = _map_areas(builder, game)
    ids = _Ids(builder)
    encounters: list[WildEncounter] = []
    for version, symbol in game.pret_versions:
        seen: dict[tuple[int, str, tuple[str, ...]], WildTable] = {}
        for table in wild_tables(repo, symbol):
            if table.map_const not in areas:
                continue
            area_id = _single_area(table.map_const, areas[table.map_const])
            key = (area_id, table.method, table.conditions)
            if key in seen:
                if seen[key].slots != table.slots:
                    maps = f"{seen[key].map_const} et {table.map_const}"
                    raise ValueError(f"map_areas.csv : {maps} partagent une zone mais pas leur table {key[1:]}")
                continue
            seen[key] = table
            encounters += ids.encounters(ids.versions[version], area_id, table)
    return encounters


def gen2_battle_notes(builder: DatabaseBuilder, game: Game) -> list[BattleNote]:
    """Notes des combats scriptés à objet forcé ou chromatiques du jeu."""
    repo = builder.gen2_repo(game, "les combats scriptés")
    areas = _map_areas(builder, game)
    ids = _Ids(builder)
    versions = frozenset(ids.versions[version] for version, _ in game.pret_versions)
    notes = []
    for battle in special_battles(repo):
        if battle.map_const not in areas:
            raise ValueError(f"Combat scripté sur une carte sans zone (map_areas.csv) : {battle}")
        note = _battle_note(builder, battle, repo.wild_held_items[battle.species][0], repo.machines)
        if note:
            species = ids.species[species_identifier(battle.species)]
            notes.append(BattleNote(versions, frozenset(areas[battle.map_const]), species, note))
    return notes


def _battle_note(builder: DatabaseBuilder, battle: SpecialBattle, item: str, machines: dict[str, str]) -> str | None:
    """Texte de la note : l'objet 1 que BATTLETYPE_FORCEITEM fait toujours tenir (LoadEnemyMon), s'il y en a un, ou
    la couleur chromatique de BATTLETYPE_FORCESHINY."""
    match battle.battle_type:
        case "BATTLETYPE_FORCEITEM":
            if item == _NO_ITEM:
                return None
            return f"Tient toujours l'objet {builder.items.name_of(item_identifier(item, machines))}"
        case "BATTLETYPE_FORCESHINY":
            return "Toujours chromatique"
        case _:
            raise ValueError(f"Type de combat sans note : {battle}")


def _map_areas(builder: DatabaseBuilder, game: Game) -> dict[str, list[int]]:
    """Carte affichée du jeu -> zones de map_areas.csv."""
    if game.version_group not in builder.map_data:
        raise ValueError(f"Cartes de {game.version_group} nécessaires pour rattacher ses rencontres à leurs zones")
    placed = {row.const for row in builder.map_data[game.version_group].maps}
    area_ids = builder.locations.area_ids
    result: dict[str, list[int]] = defaultdict(list)
    for const, key in read_map_areas().get(game.map_family, []):
        if const not in placed:
            continue
        if key not in area_ids:
            raise ValueError(f"map_areas.csv : zone inconnue de PokéAPI et de extra_areas.csv : {key}")
        result[const].append(area_ids[key])
    return result


def _single_area(const: str, areas: list[int]) -> int:
    if len(areas) != 1:
        raise ValueError(f"map_areas.csv : {const} a des rencontres aléatoires et {len(areas)} zones au lieu d'une")
    return areas[0]


class _Ids:
    """Identifiants PokéAPI des versions, espèces, méthodes et conditions."""

    def __init__(self, builder: DatabaseBuilder) -> None:
        self.versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
        self.species = {row["identifier"]: species_id for species_id, row in builder.species.items()}
        self.methods = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_methods")}
        self.conditions = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_condition_values")}

    def encounters(self, version_id: int, area_id: int, table: WildTable) -> list[WildEncounter]:
        conditions = tuple(sorted(self.conditions[condition] for condition in table.conditions))
        return [
            WildEncounter(
                version_id,
                area_id,
                self.species[species_identifier(slot.species)],
                self.methods[table.method],
                conditions,
                slot.min_level,
                slot.max_level,
                slot.chance,
            )
            for slot in table.slots
        ]
