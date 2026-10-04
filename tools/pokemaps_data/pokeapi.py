"""Lecture des CSV PokéAPI : noms français, descriptions, tailles et poids."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

FRENCH = 5
ENGLISH = 9


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _clean(text: str) -> str:
    """Normalise les sauts de ligne et espaces des textes du Pokédex."""
    return " ".join(text.replace("\f", " ").replace("­", "").split())


@dataclass(frozen=True)
class SpeciesInfo:
    name_fr: str
    name_en: str
    genus_fr: str
    height_dm: int
    weight_hg: int
    description_fr: str | None


@dataclass
class PokeApi:
    root: Path

    def _csv(self, name: str) -> list[dict[str, str]]:
        return _rows(self.root / f"{name}.csv")

    @cached_property
    def species(self) -> dict[int, SpeciesInfo]:
        names: dict[int, dict[int, dict[str, str]]] = {}
        for row in self._csv("pokemon_species_names"):
            names.setdefault(int(row["pokemon_species_id"]), {})[int(row["local_language_id"])] = row

        # Description française : la plus ancienne version disponible en français.
        descriptions: dict[int, tuple[int, str]] = {}
        for row in self._csv("pokemon_species_flavor_text"):
            if int(row["language_id"]) != FRENCH:
                continue
            species_id, version = int(row["species_id"]), int(row["version_id"])
            if species_id not in descriptions or version < descriptions[species_id][0]:
                descriptions[species_id] = (version, _clean(row["flavor_text"]))

        sizes = {}
        for row in self._csv("pokemon"):
            if row["is_default"] == "1":
                sizes[int(row["species_id"])] = (int(row["height"]), int(row["weight"]))

        result = {}
        for species_id, by_lang in names.items():
            if species_id not in sizes:
                continue
            height, weight = sizes[species_id]
            result[species_id] = SpeciesInfo(
                name_fr=by_lang[FRENCH]["name"],
                name_en=by_lang[ENGLISH]["name"],
                genus_fr=by_lang[FRENCH]["genus"],
                height_dm=height,
                weight_hg=weight,
                description_fr=descriptions.get(species_id, (0, None))[1],
            )
        return result

    def _names(self, entity: str, id_column: str) -> dict[str, str]:
        """Identifiant PokéAPI (ex. `thunder-stone`) -> nom français."""
        identifiers = {row["id"]: row["identifier"] for row in self._csv(f"{entity}s")}
        return {
            identifiers[row[id_column]]: row["name"]
            for row in self._csv(f"{entity}_names")
            if int(row["local_language_id"]) == FRENCH and row[id_column] in identifiers
        }

    @cached_property
    def move_names_fr(self) -> dict[int, str]:
        """Numéro d'attaque -> nom français."""
        return {
            int(row["move_id"]): row["name"]
            for row in self._csv("move_names")
            if int(row["local_language_id"]) == FRENCH
        }

    @cached_property
    def move_identifiers(self) -> dict[int, str]:
        return {int(row["id"]): row["identifier"] for row in self._csv("moves")}

    @cached_property
    def type_names_fr(self) -> dict[str, str]:
        return self._names("type", "type_id")

    @cached_property
    def item_names_fr(self) -> dict[str, str]:
        return self._names("item", "item_id")
