"""Comparaison explicite des tables pret avec les rencontres PokéAPI remplacées."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .games import PretFormat
from .pret_gen3_wild import REPLACED_METHODS

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_wild_gen2 import WildEncounter


@dataclass(frozen=True)
class Difference:
    version: str
    area: str
    method: str
    pokeapi: tuple[tuple[int, int, int, int], ...]
    pret: tuple[tuple[int, int, int, int], ...]


def compare_wild_tables(builder: DatabaseBuilder) -> tuple[Difference, ...]:
    slots = builder.api.by_id("encounter_slots")
    methods = builder.encounters.method_identifiers
    versions_used = {
        int(row["id"])
        for row in builder.version_rows
        if builder.game_of(int(row["version_group_id"])).pret_format is PretFormat.GEN3
    }
    old: dict[tuple[int, int, int], dict[int, tuple[int, int, int]]] = defaultdict(dict)
    new: dict[tuple[int, int, int], dict[int, tuple[int, int, int]]] = defaultdict(dict)
    for row in builder.api.table("encounters"):
        version = int(row["version_id"])
        slot = slots[int(row["encounter_slot_id"])]
        method = int(slot["encounter_method_id"])
        if version not in versions_used or methods[method] not in REPLACED_METHODS:
            continue
        key = (version, int(row["location_area_id"]), method)
        species = builder.species_of_pokemon[int(row["pokemon_id"])]
        _add(old[key], species, int(row["min_level"]), int(row["max_level"]), int(slot["rarity"]))
    for data in builder.encounters.gen3_wild.values():
        for encounter in data.encounters:
            _add_encounter(new, encounter)
    versions = {int(row["id"]): row["identifier"] for row in builder.version_rows}
    areas = builder.locations.area_keys
    return tuple(
        Difference(versions[key[0]], areas[key[1]], methods[key[2]], _signature(old[key]), _signature(new[key]))
        for key in sorted(old.keys() | new.keys())
        if old[key] != new[key]
    )


def _add_encounter(tables: dict[tuple[int, int, int], dict[int, tuple[int, int, int]]], row: WildEncounter) -> None:
    _add(tables[(row.version_id, row.area_id, row.method_id)], row.species_id, row.min_level, row.max_level, row.chance)


def _add(table: dict[int, tuple[int, int, int]], species: int, low: int, high: int, chance: int) -> None:
    previous = table.get(species)
    table[species] = (
        (min(previous[0], low), max(previous[1], high), previous[2] + chance) if previous else (low, high, chance)
    )


def _signature(table: dict[int, tuple[int, int, int]]) -> tuple[tuple[int, int, int, int], ...]:
    return tuple((species, *values) for species, values in sorted(table.items()))
