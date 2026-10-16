"""Comparaison explicite des tables du moteur DS avec les rencontres PokéAPI qu'elles remplacent.

Les deux sources n'écrivent pas les conditions de la même façon : le moteur omet une condition qui ne change pas
l'espèce d'un emplacement, PokéAPI la répète souvent. Elles sont donc comparées par ce que le joueur rencontre : pour
chaque version, zone et méthode, et pour chaque combinaison des conditions présentes dans l'une ou l'autre source
(comme validate_encounters_gen4), chaque espèce avec ses niveaux extrêmes et sa probabilité cumulée.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .games import PretFormat
from .pret_gen4_wild import REPLACED_METHODS
from .validate_encounters_gen4 import condition_combinations

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

Signature = tuple[tuple[int, int, int, float], ...]
# Espèce, niveaux minimal et maximal, probabilité, conditions.
_Row = tuple[int, int, int, float, frozenset[str]]
_Tables = dict[tuple[int, int, int], list[_Row]]


@dataclass(frozen=True)
class Difference:
    """Table dont au moins une combinaison de conditions diffère : la première, et leur nombre."""

    version: str
    area: str
    method: str
    conditions: tuple[str, ...]
    combinations: int
    pokeapi: Signature
    pret: Signature


def compare_gen4_tables(builder: DatabaseBuilder) -> tuple[Difference, ...]:
    old, new = _pokeapi_tables(builder), _engine_tables(builder)
    versions = {int(row["id"]): row["identifier"] for row in builder.version_rows}
    areas, methods = builder.locations.area_keys, builder.encounters.method_identifiers
    result = []
    for key in sorted(old.keys() | new.keys()):
        rows_old, rows_new = old.get(key, []), new.get(key, [])
        combinations = condition_combinations(row[4] for row in (*rows_old, *rows_new))
        if combinations is None:
            raise ValueError(f"comparaison DS : trop de combinaisons de conditions pour {key}")
        differing = [
            (selected, _signature(rows_old, selected), _signature(rows_new, selected))
            for selected in sorted(combinations, key=sorted)
        ]
        differing = [entry for entry in differing if entry[1] != entry[2]]
        if differing:
            selected, pokeapi, pret = differing[0]
            version, area, method = versions[key[0]], areas[key[1]], methods[key[2]]
            result.append(Difference(version, area, method, tuple(sorted(selected)), len(differing), pokeapi, pret))
    return tuple(result)


def _pokeapi_tables(builder: DatabaseBuilder) -> _Tables:
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
    tables: _Tables = defaultdict(list)
    for row in builder.api.table("encounters"):
        version, slot = int(row["version_id"]), slots[int(row["encounter_slot_id"])]
        method = int(slot["encounter_method_id"])
        if version not in versions_used or methods[method] not in REPLACED_METHODS:
            continue
        conditions = frozenset(names[value] for value in raw[int(row["id"])])
        species = builder.species_of_pokemon[int(row["pokemon_id"])]
        low, high, chance = int(row["min_level"]), int(row["max_level"]), float(slot["rarity"])
        tables[(version, int(row["location_area_id"]), method)].append((species, low, high, chance, conditions))
    return tables


def _engine_tables(builder: DatabaseBuilder) -> _Tables:
    names = {int(row["id"]): row["identifier"] for row in builder.api.table("encounter_condition_values")}
    tables: _Tables = defaultdict(list)
    for data in builder.encounters.gen4_wild.values():
        for row in data.encounters:
            conditions = frozenset(names[value] for value in row.conditions)
            key = (row.version_id, row.area_id, row.method_id)
            tables[key].append((row.species_id, row.min_level, row.max_level, row.chance, conditions))
    return tables


def _signature(rows: list[_Row], selected: frozenset[str]) -> Signature:
    """Rencontres retenues par la combinaison `selected` : par espèce, niveaux extrêmes et probabilité cumulée."""
    table: dict[int, tuple[int, int, float]] = {}
    for species, low, high, chance, conditions in rows:
        if conditions <= selected:
            first, last, total = table.get(species, (low, high, 0.0))
            table[species] = (min(first, low), max(last, high), total + chance)
    return tuple((species, low, high, round(chance, 4)) for species, (low, high, chance) in sorted(table.items()))
