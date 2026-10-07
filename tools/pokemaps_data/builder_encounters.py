"""Tables des lieux et des rencontres, corrigées par les fichiers maintenus dans tools/data/."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING

from .games import ONE_OFF_METHODS
from .pokeapi import optional_int
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


_CURATION_ACTIONS = frozenset({"exclude", "note", "trade_for"})


def _area_key(location_identifier: str, area_identifier: str) -> str:
    return f"{location_identifier}/{area_identifier}" if area_identifier else location_identifier


@dataclass
class EncounterGroup:
    version_id: int
    location_area_id: int
    pokemon_id: int
    method_id: int
    conditions: tuple[int, ...]
    min_level: int
    max_level: int
    chance: float | None
    quantity: int
    notes: list[str] = field(default_factory=list)

    def add(self, low: int, high: int, rarity: int) -> None:
        """Fusionne un emplacement de rencontre : probabilités cumulées, ou un exemplaire de plus."""
        self.min_level = min(self.min_level, low)
        self.max_level = max(self.max_level, high)
        if self.chance is None:
            self.quantity += 1
        else:
            self.chance += rarity
            self.quantity = 1


class EncounterTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    @cached_property
    def raw_encounters(self) -> list[dict[str, str]]:
        return [row for row in self.api.table("encounters") if int(row["version_id"]) in self.builder.version_ids]

    @cached_property
    def used_areas(self) -> set[int]:
        return {int(row["location_area_id"]) for row in self.raw_encounters}

    @cached_property
    def name_fixes(self) -> dict[tuple[str, str], str]:
        with (DATA_DIR / "name_fixes.csv").open(encoding="utf-8", newline="") as handle:
            return {(row["kind"], row["key"]): row["name_fr"] for row in csv.DictReader(handle)}

    @cached_property
    def area_keys(self) -> dict[int, str]:
        """Zone -> clé lisible `lieu/zone` utilisée par les fichiers de tools/data/."""
        locations = self.api.by_id("locations")
        return {
            int(row["id"]): _area_key(locations[int(row["location_id"])]["identifier"], row["identifier"])
            for row in self.api.table("location_areas")
        }

    def location_area_table(self) -> list[tuple]:
        names = self.api.names("location_area_prose", "location_area_id")
        areas = self.api.by_id("location_areas")
        locations = self.api.by_id("locations")
        location_names = self.api.names("location_names", "location_id")
        rows = []
        for area_id in sorted(self.used_areas):
            area = areas[area_id]
            location = locations[int(area["location_id"])]
            name = self.name_fixes.get(("area", self.area_keys[area_id])) or names.get(area_id)
            if not name:
                base = location_names.get(int(location["id"]), location["identifier"])
                name = f"{base} ({area['identifier']})" if area["identifier"] else base
            rows.append((area_id, int(area["location_id"]), area["identifier"], name))
        return rows

    @cached_property
    def location_rows(self) -> list[tuple]:
        names = self.api.names("location_names", "location_id")
        locations = self.api.by_id("locations")
        areas = self.api.by_id("location_areas")
        used = sorted({int(areas[area]["location_id"]) for area in self.used_areas})
        rows = []
        for location_id in used:
            row = locations[location_id]
            name = self.name_fixes.get(("location", row["identifier"])) or names.get(location_id)
            if not name:
                raise ValueError(f"Nom français manquant pour le lieu {row['identifier']} (tools/data/name_fixes.csv)")
            rows.append((location_id, row["identifier"], name, optional_int(row["region_id"])))
        return rows

    @cached_property
    def encounter_groups(self) -> list[EncounterGroup]:
        slots = self.api.by_id("encounter_slots")
        methods = self.api.by_id("encounter_methods")
        conditions = self._non_default_conditions()
        groups: dict[tuple, EncounterGroup] = {}
        for row in self.raw_encounters:
            slot = slots[int(row["encounter_slot_id"])]
            method_id = int(slot["encounter_method_id"])
            key = (
                int(row["version_id"]),
                int(row["location_area_id"]),
                int(row["pokemon_id"]),
                method_id,
                tuple(sorted(conditions[int(row["id"])])),
            )
            low, high = int(row["min_level"]), int(row["max_level"])
            if key not in groups:
                one_off = methods[method_id]["identifier"] in ONE_OFF_METHODS
                species = self.builder.species_of_pokemon[int(row["pokemon_id"])]
                groups[key] = EncounterGroup(
                    key[0], key[1], species, method_id, key[4], low, high, None if one_off else 0.0, 0
                )
            groups[key].add(low, high, int(slot["rarity"]))
        return self._apply_curation(list(groups.values()))

    def _non_default_conditions(self) -> dict[int, set[int]]:
        """Rencontre -> conditions qui la restreignent (heure, saison…), hors valeurs par défaut."""
        default_conditions = {
            int(row["id"]) for row in self.api.table("encounter_condition_values") if row["is_default"] == "1"
        }
        conditions: dict[int, set[int]] = defaultdict(set)
        for row in self.api.table("encounter_condition_value_map"):
            value = int(row["encounter_condition_value_id"])
            if value not in default_conditions:
                conditions[int(row["encounter_id"])].add(value)
        return conditions

    def _apply_curation(self, groups: list[EncounterGroup]) -> list[EncounterGroup]:
        versions = {row["identifier"]: int(row["id"]) for row in self.api.table("versions")}
        species = {row["identifier"]: int(row["id"]) for row in self.api.table("pokemon_species")}
        methods = {row["identifier"]: int(row["id"]) for row in self.api.table("encounter_methods")}
        areas = {key: area_id for area_id, key in self.area_keys.items()}
        names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
        excluded: set[int] = set()
        with (DATA_DIR / "encounter_curation.csv").open(encoding="utf-8", newline="") as handle:
            for line, row in enumerate(csv.DictReader(handle), start=2):
                if row["action"] not in _CURATION_ACTIONS:
                    raise ValueError(f"encounter_curation.csv:{line} : action inconnue {row['action']}")
                version_ids = [
                    versions[v] for v in row["versions"].split("|") if versions[v] in self.builder.version_ids
                ]
                if not version_ids:
                    continue
                target = (areas[row["location_area"]], species[row["pokemon"]], methods[row["method"]])
                matches = [
                    index
                    for index, group in enumerate(groups)
                    if group.version_id in version_ids
                    and (group.location_area_id, group.pokemon_id, group.method_id) == target
                ]
                if not matches:
                    raise ValueError(f"encounter_curation.csv:{line} ne correspond à aucune rencontre : {row}")
                if row["action"] == "exclude":
                    excluded.update(matches)
                for index in matches:
                    if row["action"] == "note":
                        groups[index].notes.append(row["value"])
                    elif row["action"] == "trade_for":
                        groups[index].notes.append(f"Échange contre {names_fr[species[row['value']]]}")
        return [group for index, group in enumerate(groups) if index not in excluded]

    @cached_property
    def method_rank(self) -> dict[int, int]:
        return {int(row["id"]): int(row["order"]) for row in self.api.table("encounter_methods")}

    def encounter_tables(self) -> tuple[list[tuple], list[tuple]]:
        groups = sorted(
            self.encounter_groups,
            key=lambda g: (
                g.version_id,
                g.location_area_id,
                self.method_rank[g.method_id],
                g.conditions,
                -(g.chance or 0),
                g.pokemon_id,
            ),
        )
        encounters, conditions = [], []
        for index, group in enumerate(groups, start=1):
            encounters.append(
                (
                    index,
                    group.version_id,
                    group.location_area_id,
                    group.pokemon_id,
                    group.method_id,
                    group.min_level,
                    group.max_level,
                    group.chance,
                    group.quantity,
                    " ; ".join(group.notes) or None,
                )
            )
            conditions += [(index, value) for value in group.conditions]
        return encounters, conditions

    def encounter_method_table(self) -> list[tuple]:
        names = self.api.names("encounter_method_prose", "encounter_method_id")
        used = {group.method_id for group in self.encounter_groups}
        return [
            (
                int(row["id"]),
                row["identifier"],
                names[int(row["id"])],
                int(row["order"]),
                int(row["identifier"] in ONE_OFF_METHODS),
            )
            for row in self.api.table("encounter_methods")
            if int(row["id"]) in used
        ]

    def encounter_condition_value_table(self) -> list[tuple]:
        names = self.api.names("encounter_condition_value_prose", "encounter_condition_value_id")
        used = {value for group in self.encounter_groups for value in group.conditions}
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])])
            for row in self.api.table("encounter_condition_values")
            if int(row["id"]) in used
        ]

    def encounter_rate_table(self) -> list[tuple]:
        version_ids, used_areas = self.builder.version_ids, self.used_areas
        return sorted(
            (int(row["version_id"]), int(row["location_area_id"]), int(row["encounter_method_id"]), int(row["rate"]))
            for row in self.api.table("location_area_encounter_rates")
            if int(row["version_id"]) in version_ids and int(row["location_area_id"]) in used_areas
        )
