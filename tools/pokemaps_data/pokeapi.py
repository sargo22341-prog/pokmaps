"""Accès aux CSV PokéAPI : chargement paresseux des tables et noms localisés."""

from __future__ import annotations

import csv
from functools import cache
from pathlib import Path

FRENCH = 5
ENGLISH = 9


def clean_text(text: str) -> str:
    """Normalise les sauts de ligne et espaces des textes du jeu."""
    return " ".join(text.replace("\f", " ").replace("­", "").split())


class PokeApi:
    def __init__(self, root: Path) -> None:
        self.root = root

    @cache  # noqa: B019 (une seule instance par build)
    def table(self, name: str) -> tuple[dict[str, str], ...]:
        with (self.root / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
            return tuple(csv.DictReader(handle))

    @cache  # noqa: B019
    def by_id(self, name: str) -> dict[int, dict[str, str]]:
        return {int(row["id"]): row for row in self.table(name)}

    @cache  # noqa: B019
    def names(self, table: str, id_column: str, language: int = FRENCH, column: str = "name") -> dict[int, str]:
        """Noms localisés d'une table `*_names` / `*_prose` : identifiant -> texte."""
        return {
            int(row[id_column]): row[column]
            for row in self.table(table)
            if int(row["local_language_id"]) == language and row[column]
        }


def optional_int(value: str) -> int | None:
    return int(value) if value else None
