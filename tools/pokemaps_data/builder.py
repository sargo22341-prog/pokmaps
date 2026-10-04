"""Assemble les données pret + PokéAPI et écrit pokedex.db."""

from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from . import pret
from .pokeapi import PokeApi
from .pret import PretGame

# Version du schéma : doit correspondre à la version de la base Room dans l'application.
SCHEMA_VERSION = 1

SCHEMA = Path(__file__).with_name("schema.sql")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VERSION_GROUPS = ((1, "red-blue", "Rouge / Bleu"), (2, "yellow", "Jaune"))

# Types pret -> identifiant PokéAPI. Les types spéciaux sont ceux déclarés après SPECIAL
# dans constants/type_constants.asm.
TYPE_IDENTIFIERS = {
    "NORMAL": "normal",
    "FIGHTING": "fighting",
    "FLYING": "flying",
    "POISON": "poison",
    "GROUND": "ground",
    "ROCK": "rock",
    "BUG": "bug",
    "GHOST": "ghost",
    "FIRE": "fire",
    "WATER": "water",
    "GRASS": "grass",
    "ELECTRIC": "electric",
    "PSYCHIC_TYPE": "psychic",
    "ICE": "ice",
    "DRAGON": "dragon",
}
SPECIAL_TYPES = {"FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC_TYPE", "ICE", "DRAGON"}

# Ordre d'affichage des méthodes de rencontre.
METHOD_ORDER = (
    pret.WALK,
    pret.SURF,
    pret.OLD_ROD,
    pret.GOOD_ROD,
    pret.SUPER_ROD,
    pret.STATIC,
    "GIFT",
    "FOSSIL",
    "PURCHASE",
    pret.PRIZE,
    pret.TRADE,
)


@dataclass(frozen=True)
class Version:
    id: int
    identifier: str
    name_fr: str
    version_group_id: int
    game: PretGame
    code: str  # lettre utilisée dans special_encounters.csv


@dataclass
class EncounterRow:
    version_id: int
    location_id: int
    pokemon_id: int
    method: str
    min_level: int | None
    max_level: int | None
    chance: float | None
    note_fr: str | None


class DatabaseBuilder:
    def __init__(self, pret_red_blue: Path, pret_yellow: Path, pokeapi_csv: Path) -> None:
        red = PretGame(pret_red_blue, {"_RED"})
        blue = PretGame(pret_red_blue, {"_BLUE"})
        yellow = PretGame(pret_yellow, {"_YELLOW"})
        self.versions = (
            Version(1, "red", "Rouge", 1, red, "R"),
            Version(2, "blue", "Bleu", 1, blue, "B"),
            Version(3, "yellow", "Jaune", 2, yellow, "Y"),
        )
        # Jeu de référence pour chaque groupe de versions (Rouge et Bleu ont les mêmes données Pokémon).
        self.group_games = {1: red, 2: yellow}
        self.red = red
        self.api = PokeApi(pokeapi_csv)
        self.type_ids = self._type_ids()

    # --- Helpers ------------------------------------------------------------

    def _type_ids(self) -> dict[str, int]:
        rows = csv.DictReader((self.api.root / "types.csv").open(encoding="utf-8"))
        by_identifier = {row["identifier"]: int(row["id"]) for row in rows}
        return {name: by_identifier[identifier] for name, identifier in TYPE_IDENTIFIERS.items()}

    def dex(self, species: str) -> int:
        return self.red.dex_of(species)

    def location_id(self, game: PretGame, map_name: str) -> int:
        """Numéro de carte, commun aux trois versions (seuls certains noms diffèrent dans Jaune)."""
        return game.map_ids[map_name]

    # --- Construction des lignes -------------------------------------------

    def locations(self) -> list[tuple]:
        names = {}
        with (DATA_DIR / "locations_fr.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                names[row["map"]] = row
        ids: dict[int, str] = {}
        for version in self.versions:
            for map_name, map_id in version.game.map_ids.items():
                ids.setdefault(map_id, map_name)
        rows = []
        for map_id, map_name in sorted(ids.items()):
            if map_name.startswith("UNUSED_MAP"):
                continue
            if map_name not in names:
                raise ValueError(f"Nom français manquant pour la carte {map_name} (tools/data/locations_fr.csv)")
            row = names[map_name]
            rows.append((map_id, map_name.lower(), row["name_fr"], row["area"], row["area_name_fr"], row["kind"]))
        return rows

    def types(self) -> list[tuple]:
        names = self.api.type_names_fr
        return sorted(
            (type_id, TYPE_IDENTIFIERS[name], names[TYPE_IDENTIFIERS[name]], int(name in SPECIAL_TYPES))
            for name, type_id in self.type_ids.items()
        )

    def items(self) -> list[tuple]:
        """Objets utilisés par les évolutions."""
        names = self.api.item_names_fr
        used = {evo.item for evos in self.red.evos_moves.values() for evo in evos.evolutions if evo.item}
        rows = []
        for item in sorted(used):
            identifier = item.lower().replace("_", "-")
            rows.append((self.red.item_ids[item], identifier, names[identifier]))
        return sorted(rows)

    def pokemon(self) -> list[tuple]:
        rows = []
        for species, stats in self.red.base_stats.items():
            dex = self.dex(species)
            yellow_stats = self.group_games[2].base_stats[species]
            for attribute in ("hp", "attack", "defense", "speed", "special", "types", "base_exp", "growth_rate"):
                if getattr(stats, attribute) != getattr(yellow_stats, attribute):
                    raise ValueError(f"{species} : {attribute} diffère entre Rouge/Bleu et Jaune")
            info = self.api.species[dex]
            type_ids = [self.type_ids[t] for t in stats.types]
            rows.append(
                (
                    dex,
                    species.lower(),
                    info.name_fr,
                    info.name_en,
                    info.genus_fr,
                    type_ids[0],
                    type_ids[1] if len(type_ids) > 1 else None,
                    stats.hp,
                    stats.attack,
                    stats.defense,
                    stats.speed,
                    stats.special,
                    stats.base_exp,
                    stats.growth_rate,
                    info.height_dm,
                    info.weight_hg,
                    info.description_fr,
                )
            )
        return sorted(rows)

    def pokemon_version_groups(self) -> list[tuple]:
        return sorted(
            (self.dex(species), group_id, stats.catch_rate)
            for group_id, game in self.group_games.items()
            for species, stats in game.base_stats.items()
        )

    def moves(self) -> list[tuple]:
        rows = []
        for name, move in self.red.moves.items():
            move_id = self.red.move_ids[name]
            if self.group_games[2].moves[name] != move:
                raise ValueError(f"L'attaque {name} diffère entre Rouge/Bleu et Jaune")
            rows.append(
                (
                    move_id,
                    self.api.move_identifiers[move_id],
                    self.api.move_names_fr[move_id],
                    self.type_ids[move.type],
                    move.power,
                    move.accuracy,
                    move.pp,
                    move.effect,
                )
            )
        return sorted(rows)

    def machines(self) -> list[tuple]:
        if self.red.machines != self.group_games[2].machines:
            raise ValueError("Les CT/CS diffèrent entre Rouge/Bleu et Jaune")
        return [
            (index, int(kind == "HM"), number, self.red.move_ids[move])
            for index, (kind, number, move) in enumerate(self.red.machines, start=1)
        ]

    def pokemon_moves(self) -> list[tuple]:
        rows: set[tuple] = set()
        for group_id, game in self.group_games.items():
            machine_moves = {move for _, _, move in game.machines}
            for species, stats in game.base_stats.items():
                dex = self.dex(species)
                for move in stats.start_moves:
                    rows.add((dex, group_id, game.move_ids[move], "START", 1))
                for level, move in game.evos_moves[species].learnset:
                    rows.add((dex, group_id, game.move_ids[move], "LEVEL", level))
                for move in stats.tmhm:
                    if move == "UNUSED":
                        continue
                    if move not in machine_moves:
                        raise ValueError(f"{species} : {move} n'est pas une CT/CS")
                    rows.add((dex, group_id, game.move_ids[move], "MACHINE", 0))
        return sorted(rows)

    def evolutions(self) -> list[tuple]:
        rows = []
        for species, evos in self.red.evos_moves.items():
            if evos.evolutions != self.group_games[2].evos_moves[species].evolutions:
                raise ValueError(f"Les évolutions de {species} diffèrent entre Rouge/Bleu et Jaune")
            for evo in evos.evolutions:
                item_id = self.red.item_ids[evo.item] if evo.item else None
                rows.append((self.dex(species), self.dex(evo.species), evo.method, evo.level, item_id))
        return sorted(rows)

    def encounter_rates(self) -> list[tuple]:
        rows = set()
        for version in self.versions:
            for table in version.game.wild_encounters:
                location = self.location_id(version.game, table.map_name)
                rows.add((version.id, location, table.method, table.rate))
        return sorted(rows)

    def encounters(self) -> list[tuple]:
        rows: list[EncounterRow] = []
        for version in self.versions:
            rows += self._random_encounters(version)
            rows += self._special_encounters(version)
        method_rank = {method: rank for rank, method in enumerate(METHOD_ORDER)}
        rows.sort(key=lambda r: (r.version_id, r.location_id, method_rank[r.method], -(r.chance or 0), r.pokemon_id))
        return [
            (
                index,
                r.version_id,
                r.location_id,
                r.pokemon_id,
                r.method,
                r.min_level,
                r.max_level,
                None if r.chance is None else round(r.chance, 2),
                r.note_fr,
            )
            for index, r in enumerate(rows, start=1)
        ]

    def _random_encounters(self, version: Version) -> Iterable[EncounterRow]:
        game = version.game
        merged: dict[tuple[int, int, str], EncounterRow] = {}
        for table in game.wild_encounters + game.fishing_encounters:
            location = self.location_id(game, table.map_name)
            for slot in table.slots:
                key = (location, self.dex(slot.species), table.method)
                row = merged.get(key)
                if row is None:
                    merged[key] = EncounterRow(
                        version.id, location, key[1], table.method, slot.level, slot.level, slot.chance, None
                    )
                else:
                    row.min_level = min(row.min_level, slot.level)
                    row.max_level = max(row.max_level, slot.level)
                    row.chance += slot.chance
        return merged.values()

    def _special_encounters(self, version: Version) -> Iterable[EncounterRow]:
        game = version.game
        rows = []
        for static in game.static_encounters:
            note = None
            if static.map_name == "POWER_PLANT" and static.species in ("VOLTORB", "ELECTRODE"):
                note = "Déguisé en Poké Ball"
            if static.count > 1:
                note = f"{note} ({static.count} exemplaires)" if note else f"{static.count} exemplaires"
            rows.append(
                EncounterRow(
                    version.id,
                    self.location_id(game, static.map_name),
                    self.dex(static.species),
                    pret.STATIC,
                    static.level,
                    static.level,
                    None,
                    note,
                )
            )
        species_names = self.api.species
        for trade in game.trades:
            given = species_names[self.dex(trade.give)].name_fr
            rows.append(
                EncounterRow(
                    version.id,
                    self.location_id(game, trade.map_name),
                    self.dex(trade.get),
                    pret.TRADE,
                    None,
                    None,
                    None,
                    f"Échange contre {given} (surnom {trade.nickname})",
                )
            )
        prize_room = self.location_id(game, "GAME_CORNER_PRIZE_ROOM")
        for prize in game.prizes:
            rows.append(
                EncounterRow(
                    version.id,
                    prize_room,
                    self.dex(prize.species),
                    pret.PRIZE,
                    prize.level,
                    prize.level,
                    None,
                    f"{prize.cost} jetons",
                )
            )
        with (DATA_DIR / "special_encounters.csv").open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if version.code not in row["versions"]:
                    continue
                level = int(row["level"])
                rows.append(
                    EncounterRow(
                        version.id,
                        # Les cartes de ce fichier utilisent les noms de pokered.
                        self.location_id(self.red, row["map"]),
                        self.dex(row["species"]),
                        row["method"],
                        level,
                        level,
                        None,
                        row["note_fr"] or None,
                    )
                )
        return rows

    # --- Écriture -----------------------------------------------------------

    def write(self, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp")
        tmp.unlink(missing_ok=True)
        connection = sqlite3.connect(tmp)
        try:
            connection.executescript(SCHEMA.read_text(encoding="utf-8"))
            tables = {
                "version_group": VERSION_GROUPS,
                "version": [(v.id, v.identifier, v.name_fr, v.version_group_id) for v in self.versions],
                "type": self.types(),
                "item": self.items(),
                "pokemon": self.pokemon(),
                "pokemon_version_group": self.pokemon_version_groups(),
                "move": self.moves(),
                "machine": self.machines(),
                "pokemon_move": self.pokemon_moves(),
                "evolution": self.evolutions(),
                "location": self.locations(),
                "encounter": self.encounters(),
                "encounter_rate": self.encounter_rates(),
            }
            for table, rows in tables.items():
                rows = list(rows)
                placeholders = ", ".join("?" * len(rows[0]))
                connection.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
            connection.execute("VACUUM")
        finally:
            connection.close()
        tmp.replace(output)
