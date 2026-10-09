"""Rencontres GBA reliées aux zones éditoriales, avec conditions de scénario et taux moteur."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .builder_wild_gen2 import WildEncounter
from .games import Game
from .maps import read_map_areas
from .pret_gen3_wild import WildTable, wild_tables
from .pret_identifiers import species_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


@dataclass(frozen=True)
class WildData:
    encounters: tuple[WildEncounter, ...]
    rates: tuple[tuple[int, int, int, int], ...]


def gen3_wild_data(builder: DatabaseBuilder, game: Game) -> WildData:
    repo = builder.gen3_repo(game, "les rencontres aléatoires")
    mappings: dict[str, list[str]] = defaultdict(list)
    for const, key in read_map_areas(game.version_group).get(game.map_family, []):
        mappings[const].append(key)
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    methods = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_methods")}
    species = {row["identifier"]: value for value, row in builder.species.items()}
    condition_ids = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_condition_values")}
    encounters, rates = [], []
    for version, _ in game.pret_versions:
        seen: dict[tuple[int, int, tuple[int, ...]], WildTable] = {}
        for table in wild_tables(repo, version):
            if "UNUSED" in table.map_const:
                continue  # Layouts explicitement inutilisés, exclus aussi du catalogue de cartes.
            key = _area_key(table, mappings)
            if key not in builder.locations.area_ids:
                raise ValueError(f"map_areas.csv : zone sauvage inconnue {key}")
            area, method = builder.locations.area_ids[key], methods[table.method]
            conditions = tuple(sorted(condition_ids[value] for value in _conditions(game, table.map_const)))
            identity = (area, method, conditions)
            if identity in seen:
                previous = seen[identity]
                if previous.slots != table.slots or previous.rate != table.rate:
                    raise ValueError(f"map_areas.csv : tables différentes dans {key} : {previous.label}, {table.label}")
                continue
            seen[identity] = table
            for slot in table.slots:
                identifier = species_identifier(slot.species)
                if identifier not in species:
                    raise ValueError(f"{table.label} : espèce inconnue {slot.species}")
                encounters.append(
                    WildEncounter(
                        versions[version],
                        area,
                        species[identifier],
                        method,
                        conditions,
                        slot.min_level,
                        slot.max_level,
                        slot.chance,
                    )
                )
            rates.append((versions[version], area, method, table.rate))
    return WildData(tuple(encounters), tuple(sorted(set(rates))))


def _area_key(table: WildTable, mappings: dict[str, list[str]]) -> str:
    keys = mappings.get(table.map_const, [])
    if "ALTERING_CAVE" in table.map_const:
        suffix = re.search(r"(?:Cave_?|_)([2-9])(?:_|$)", table.label)
        letter = chr(ord("a") + (int(suffix[1]) - 1 if suffix else 0))
        keys = [key for key in keys if key.endswith("/" + letter)]
    if table.map_const == "MAP_ROUTE2":
        keys = [key for key in keys if key.endswith("south-towards-viridian-city")]
    if table.map_const == "MAP_ROCK_TUNNEL_B1F":
        keys = [key for key in keys if key == "rock-tunnel/b1f"]
    if table.map_const.startswith("MAP_MAGMA_HIDEOUT"):
        keys = [key for key in keys if key == "magma-hideout"]
    if len(keys) != 1:
        raise ValueError(f"map_areas.csv : {table.label}/{table.method} : une zone attendue, reçu {keys}")
    return keys[0]


def _conditions(game: Game, const: str) -> tuple[str, ...]:
    if game.version_group == "emerald" and const in {
        "MAP_SAFARI_ZONE_NORTHEAST",
        "MAP_SAFARI_ZONE_SOUTHEAST",
        "MAP_ALTERING_CAVE",
    }:
        return ("story-progress-hall-of-fame",)
    if game.version_group == "firered-leafgreen" and (
        const.startswith(("MAP_FOUR_ISLAND", "MAP_FIVE_ISLAND", "MAP_SIX_ISLAND", "MAP_SEVEN_ISLAND"))
        or "RUBY_PATH" in const
        or const.startswith("MAP_CERULEAN_CAVE")
    ):
        return ("story-progress-hall-of-fame", "story-progress-national-dex")
    return ()
