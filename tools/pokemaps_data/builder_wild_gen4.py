"""Rencontres DS lues dans le moteur (pret_gen4_wild.py), rattachées aux zones de map_areas.csv.

Les tables du moteur remplacent les méthodes aléatoires de PokéAPI (marche, surf, cannes, arbres à Miel). Une
carte n'a qu'une zone sauvage : si elle en a plusieurs dans map_areas.csv (un don dans la même ville), la zone
sauvage est celle où PokéAPI ou extra_areas.csv placent des rencontres de ces méthodes. Deux cartes d'une même zone
doivent avoir les mêmes tables.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .builder_wild_gen2 import WildEncounter
from .maps import read_map_areas
from .maps_terrain_gen4 import has_tall_grass
from .pret_gen4_wild import REPLACED_METHODS, Gen4WildTable, WildContext, wild_tables
from .pret_gen4_wild_extra import FEEBAS, read_wild_extra
from .pret_gen4_wild_rules import read_wild_rules

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_encounters import EncounterGroup
    from .games import Game
    from .pret_gen4 import Gen4PretRepo

NoteKey = tuple[int, int, int, int, tuple[int, ...]]
_MARSH_NOTE = (
    "Pokémon du jour du Grand Marais : tiré chaque jour parmi 32 entrées (visible aux jumelles de la tour), "
    "probabilité moyenne sur les tirages."
)
_TROPHY_NOTE = (
    "Pokémon du jour annoncé au Jardin Trophée, tiré parmi 16 après le Pokédex National ; probabilité moyenne sur "
    "les tirages."
)
_SWARM_NOTE = "Essaim du jour annoncé à Littorella après le Pokédex National ; un seul lieu d'essaim par jour."
_CONDITION_NOTES = {
    "story-progress-before-national-dex": _MARSH_NOTE,
    "story-progress-national-dex": _MARSH_NOTE,
    "backlot-mentioned": _TROPHY_NOTE,
    "swarm-yes": _SWARM_NOTE,
}


@dataclass(frozen=True)
class Gen4WildData:
    encounters: tuple[WildEncounter, ...]
    rates: tuple[tuple[int, int, int, int], ...]
    # (version, zone, espèce, méthode, conditions) -> notes à joindre à la rencontre regroupée.
    notes: dict[NoteKey, tuple[str, ...]]
    version_ids: frozenset[int]
    feebas: tuple[int, int, int]  # espèce, niveau minimal et maximal du moteur
    roamers: tuple[tuple[int, int], ...]  # (espèce, niveau) des errants activés par les scripts
    roamer_routes: int


def wild_context(repo: Gen4PretRepo) -> WildContext:
    rules = read_wild_rules(repo)
    radar = frozenset(
        header.index for header in repo.headers.values() if header.encounters and has_tall_grass(repo, header, rules)
    )
    return WildContext(rules, read_wild_extra(repo.root, repo.platinum), radar)


def gen4_wild_data(builder: DatabaseBuilder, game: Game, context: WildContext) -> Gen4WildData:
    repo = builder.gen4_repo(game, "les rencontres aléatoires")
    areas = _WildAreas(builder, game)
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    methods = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_methods")}
    conditions = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_condition_values")}
    encounters: list[WildEncounter] = []
    rates: set[tuple[int, int, int, int]] = set()
    notes: dict[NoteKey, set[str]] = defaultdict(set)
    for version, _ in game.pret_versions:
        seen: dict[tuple[int, str], Gen4WildTable] = {}
        for table in wild_tables(repo, context, version):
            const = repo.headers[table.header].constant
            area = areas.area(const)
            previous = seen.setdefault((area, table.method), table)
            if (previous.slots, previous.rate, previous.note) != (table.slots, table.rate, table.note):
                raise ValueError(f"map_areas.csv : tables {table.method} différentes dans la zone {area} ({const})")
            if previous is not table:
                continue
            for slot in table.slots:
                ids = tuple(sorted(_identifier(conditions, value, "Conditions") for value in slot.conditions))
                row = WildEncounter(
                    versions[version], area, slot.species, _identifier(methods, table.method, "Méthodes"), ids,
                    slot.min_level, slot.max_level, slot.chance,
                )  # fmt: skip
                encounters.append(row)
                key = (row.version_id, area, row.species_id, row.method_id, ids)
                notes[key].update(_notes(table, slot.conditions))
            if table.rate:
                rates.add((versions[version], area, _identifier(methods, table.method, "Méthodes"), table.rate))
    rules, feebas = context.rules, context.extra[FEEBAS][0]
    return Gen4WildData(
        tuple(encounters),
        tuple(sorted(rates)),
        {key: tuple(sorted(value)) for key, value in notes.items()},
        frozenset(versions[version] for version, _ in game.pret_versions),
        (feebas, *rules.feebas[1]),
        rules.roamers,
        len(set(rules.roamer_headers)),
    )


def _identifier(ids: dict[str, int], value: str, kind: str) -> int:
    """Numéro PokéAPI d'une méthode ou d'une condition produite par le moteur."""
    if value not in ids:
        raise ValueError(f"{kind} de rencontre DS inconnues de PokéAPI : {value}")
    return ids[value]


def complete_gen4_encounters(
    builder: DatabaseBuilder, groups: list[EncounterGroup], data: dict[str, Gen4WildData]
) -> None:
    """Notes des tables du moteur ; Barpau et errants de PokéAPI vérifiés contre le moteur et annotés."""
    methods = builder.encounters.method_identifiers
    for game_data in data.values():
        for group in groups:
            if group.version_id not in game_data.version_ids:
                continue
            key = (group.version_id, group.location_area_id, group.pokemon_id, group.method_id, group.conditions)
            group.notes.extend(note for note in game_data.notes.get(key, ()) if note not in group.notes)
            match methods[group.method_id]:
                case "feebas-tile-fishing":
                    _feebas(group, game_data)
                case "roaming-grass" | "roaming-water":
                    _roamer(group, game_data)
                case _:
                    pass


def _feebas(group: EncounterGroup, data: Gen4WildData) -> None:
    species, low, high = data.feebas
    if group.pokemon_id != species:
        raise ValueError(f"Barpau du moteur ({species}) différent de PokéAPI ({group.pokemon_id})")
    group.min_level, group.max_level = low, high
    group.notes.append(
        "Quatre cases d'eau du sous-sol, tirées selon la sauvegarde et changées chaque jour : non placées sur la "
        "carte. Les trois cannes y pêchent Barpau."
    )


def _roamer(group: EncounterGroup, data: Gen4WildData) -> None:
    if (group.pokemon_id, group.max_level) not in data.roamers or group.min_level != group.max_level:
        raise ValueError(f"Errant de PokéAPI absent du moteur : {group.pokemon_id} niveau {group.max_level}")
    note = (
        f"Errant : change de lieu parmi {data.roamer_routes} routes de Sinnoh à chaque changement de carte du joueur ; "
        "une rencontre sur deux quand il est sur la route (jamais au Pokéradar ni en combat duo)."
    )
    if note not in group.notes:
        group.notes.append(note)


def _notes(table: Gen4WildTable, conditions: tuple[str, ...]) -> set[str]:
    found = {table.note} if table.note else set()
    found.update(_CONDITION_NOTES[value] for value in conditions if value in _CONDITION_NOTES)
    if "backlot-mentioned" in conditions:
        found.discard(_MARSH_NOTE)
    return found


class _WildAreas:
    """Zone sauvage de chaque en-tête, d'après map_areas.csv."""

    def __init__(self, builder: DatabaseBuilder, game: Game) -> None:
        self.ids = builder.locations.area_ids
        self.mappings: dict[str, list[str]] = defaultdict(list)
        for const, key in read_map_areas(game.version_group).get(game.map_family, []):
            self.mappings[const].append(key)
        self.wild = self._wild_areas(builder, game)

    def area(self, const: str) -> int:
        keys = [key for key in self.mappings.get(const, []) if key in self.wild]
        if len(keys) != 1:
            raise ValueError(f"map_areas.csv : {const} : une zone sauvage attendue, reçu {keys}")
        if keys[0] not in self.ids:
            raise ValueError(f"map_areas.csv : zone sauvage inconnue {keys[0]}")
        return self.ids[keys[0]]

    @staticmethod
    def _wild_areas(builder: DatabaseBuilder, game: Game) -> frozenset[str]:
        """Zones où PokéAPI place des rencontres des méthodes remplacées, et zones ajoutées (extra_areas.csv)."""
        slots = builder.api.by_id("encounter_slots")
        methods = builder.api.by_id("encounter_methods")
        names = {row["identifier"] for row in builder.version_rows if row["identifier"] in dict(game.pret_versions)}
        version_ids = {int(row["id"]) for row in builder.version_rows if row["identifier"] in names}
        keys = builder.locations.area_keys
        found = {
            keys[int(row["location_area_id"])]
            for row in builder.api.table("encounters")
            if int(row["version_id"]) in version_ids
            and methods[int(slots[int(row["encounter_slot_id"])]["encounter_method_id"])]["identifier"]
            in REPLACED_METHODS
        }
        return frozenset(found | {keys[area] for area in builder.locations.extra_areas})
