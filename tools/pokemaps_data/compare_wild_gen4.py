"""Comparaison explicite des tables du moteur DS avec les rencontres PokéAPI qu'elles remplacent.

Les deux sources sont ramenées au même modèle : par version, zone, méthode et ensemble de conditions, chaque espèce
avec ses niveaux extrêmes et sa probabilité cumulée. PokéAPI décrit, comme le moteur, chaque emplacement remplacé avec
toutes ses valeurs (sans essaim, sans Pokéradar…) : ses conditions sont comparées telles quelles.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .games import PretFormat
from .pret_gen4_wild import REPLACED_METHODS

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

Signature = tuple[tuple[int, int, int, float], ...]
_Tables = dict[tuple[int, int, int, tuple[str, ...]], dict[int, tuple[int, int, float]]]


@dataclass(frozen=True)
class Difference:
    version: str
    area: str
    method: str
    conditions: tuple[str, ...]
    pokeapi: Signature
    pret: Signature


def compare_gen4_tables(builder: DatabaseBuilder) -> tuple[Difference, ...]:
    slots = builder.api.by_id("encounter_slots")
    methods = builder.encounters.method_identifiers
    names = {int(row["id"]): row["identifier"] for row in builder.api.table("encounter_condition_values")}
    raw: dict[int, set[int]] = defaultdict(set)
    for row in builder.api.table("encounter_condition_value_map"):
        raw[int(row["encounter_id"])].add(int(row["encounter_condition_value_id"]))
    versions_used = {
        int(row["id"])
        for row in builder.version_rows
        if builder.game_of(int(row["version_group_id"])).pret_format is PretFormat.GEN4
    }
    old: _Tables = defaultdict(dict)
    new: _Tables = defaultdict(dict)
    for row in builder.api.table("encounters"):
        version, slot = int(row["version_id"]), slots[int(row["encounter_slot_id"])]
        method = int(slot["encounter_method_id"])
        if version not in versions_used or methods[method] not in REPLACED_METHODS:
            continue
        conditions = tuple(sorted(names[value] for value in raw[int(row["id"])]))
        key = (version, int(row["location_area_id"]), method, conditions)
        species = builder.species_of_pokemon[int(row["pokemon_id"])]
        _add(old[key], species, int(row["min_level"]), int(row["max_level"]), float(slot["rarity"]))
    for data in builder.encounters.gen4_wild.values():
        for encounter in data.encounters:
            conditions = tuple(sorted(names[value] for value in encounter.conditions))
            key = (encounter.version_id, encounter.area_id, encounter.method_id, conditions)
            _add(new[key], encounter.species_id, encounter.min_level, encounter.max_level, encounter.chance)
    versions = {int(row["id"]): row["identifier"] for row in builder.version_rows}
    areas = builder.locations.area_keys
    return tuple(
        Difference(versions[key[0]], areas[key[1]], methods[key[2]], key[3], _signature(old[key]), _signature(new[key]))
        for key in sorted(old.keys() | new.keys())
        if _signature(old[key]) != _signature(new[key])
    )


def _add(table: dict[int, tuple[int, int, float]], species: int, low: int, high: int, chance: float) -> None:
    previous = table.get(species)
    table[species] = (
        (min(previous[0], low), max(previous[1], high), previous[2] + chance) if previous else (low, high, chance)
    )


def _signature(table: dict[int, tuple[int, int, float]]) -> Signature:
    return tuple((species, low, high, round(chance, 4)) for species, (low, high, chance) in sorted(table.items()))
