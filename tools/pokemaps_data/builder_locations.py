"""Tables des lieux et des zones de rencontre : celles de PokéAPI, noms corrigés par tools/data/name_fixes.csv, et
zones absentes de PokéAPI ajoutées par tools/data/extra_areas.csv (avec un identifiant hors de sa plage)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cached_property

from .pokeapi import PokeApi, optional_int
from .sources import DATA_DIR


def _area_key(location_identifier: str, area_identifier: str) -> str:
    return f"{location_identifier}/{area_identifier}" if area_identifier else location_identifier


@dataclass(frozen=True)
class ExtraArea:
    """Zone absente de PokéAPI (tools/data/extra_areas.csv), avec un identifiant hors de la plage de PokéAPI."""

    id: int
    location_id: int
    identifier: str
    name_fr: str


class LocationTables:
    def __init__(self, api: PokeApi) -> None:
        self.api = api

    @cached_property
    def extra_areas(self) -> dict[int, ExtraArea]:
        locations = {row["identifier"]: int(row["id"]) for row in self.api.table("locations")}
        pokeapi = self.api.by_id("location_areas")
        result: dict[int, ExtraArea] = {}
        with (DATA_DIR / "extra_areas.csv").open(encoding="utf-8", newline="") as handle:
            for line, row in enumerate(csv.DictReader(handle), start=2):
                area_id = int(row["id"])
                if area_id in pokeapi or area_id in result or row["location"] not in locations:
                    raise ValueError(f"extra_areas.csv:{line} : identifiant pris ou lieu inconnu de PokéAPI : {row}")
                if not row["name_fr"].strip():
                    raise ValueError(f"extra_areas.csv:{line} : nom vide")
                result[area_id] = ExtraArea(area_id, locations[row["location"]], row["area"], row["name_fr"])
        return result

    @cached_property
    def area_keys(self) -> dict[int, str]:
        """Zone -> clé lisible `lieu/zone` utilisée par les fichiers de tools/data/."""
        locations = self.api.by_id("locations")
        keys = {
            int(row["id"]): _area_key(locations[int(row["location_id"])]["identifier"], row["identifier"])
            for row in self.api.table("location_areas")
        }
        for area in self.extra_areas.values():
            keys[area.id] = _area_key(locations[area.location_id]["identifier"], area.identifier)
        if len(set(keys.values())) != len(keys):
            raise ValueError("extra_areas.csv : une zone ajoutée existe déjà dans PokéAPI")
        return keys

    @cached_property
    def area_ids(self) -> dict[str, int]:
        return {key: area_id for area_id, key in self.area_keys.items()}

    @cached_property
    def name_fixes(self) -> dict[tuple[str, str], str]:
        with (DATA_DIR / "name_fixes.csv").open(encoding="utf-8", newline="") as handle:
            return {(row["kind"], row["key"]): row["name_fr"] for row in csv.DictReader(handle)}

    def location_area_table(self, used_areas: set[int]) -> list[tuple]:
        """Zones `used_areas`, avec leur nom français (corrigé par name_fixes.csv ou donné par extra_areas.csv)."""
        names = self.api.names("location_area_prose", "location_area_id")
        locations = self.api.by_id("locations")
        location_names = self.api.names("location_names", "location_id")
        rows = []
        for area_id in sorted(used_areas):
            location_id, identifier = self._area(area_id)
            name = self.name_fixes.get(("area", self.area_keys[area_id])) or names.get(area_id)
            if area_id in self.extra_areas:
                name = self.extra_areas[area_id].name_fr
            if not name:
                base = location_names.get(location_id, locations[location_id]["identifier"])
                name = f"{base} ({identifier})" if identifier else base
            rows.append((area_id, location_id, identifier, name))
        return rows

    def _area(self, area_id: int) -> tuple[int, str]:
        if area_id in self.extra_areas:
            return self.extra_areas[area_id].location_id, self.extra_areas[area_id].identifier
        row = self.api.by_id("location_areas")[area_id]
        return int(row["location_id"]), row["identifier"]

    def location_rows(self, used_areas: set[int]) -> list[tuple]:
        """Lieux des zones `used_areas` ; un nom français manquant arrête la génération."""
        names = self.api.names("location_names", "location_id")
        locations = self.api.by_id("locations")
        used = sorted({self._area(area)[0] for area in used_areas})
        rows = []
        for location_id in used:
            row = locations[location_id]
            name = self.name_fixes.get(("location", row["identifier"])) or names.get(location_id)
            if not name:
                raise ValueError(f"Nom français manquant pour le lieu {row['identifier']} (tools/data/name_fixes.csv)")
            rows.append((location_id, row["identifier"], name, optional_int(row["region_id"])))
        return rows
