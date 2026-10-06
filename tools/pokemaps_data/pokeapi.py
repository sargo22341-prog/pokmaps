"""Accès aux CSV PokéAPI : chargement paresseux des tables et noms localisés."""

from __future__ import annotations

import csv
from pathlib import Path

FRENCH = 5
ENGLISH = 9


def clean_text(text: str) -> str:
    """Normalise les sauts de ligne et espaces des textes du jeu."""
    return " ".join(text.replace("\f", " ").replace("­", "").split())


class PokeApi:
    """Tables PokéAPI lues une seule fois puis gardées en mémoire pour toute la génération."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._tables: dict[str, tuple[dict[str, str], ...]] = {}
        self._by_id: dict[str, dict[int, dict[str, str]]] = {}
        self._names: dict[tuple[str, str, int, str], dict[int, str]] = {}

    def table(self, name: str) -> tuple[dict[str, str], ...]:
        if name not in self._tables:
            with (self.root / f"{name}.csv").open(encoding="utf-8", newline="") as handle:
                self._tables[name] = tuple(csv.DictReader(handle))
        return self._tables[name]

    def by_id(self, name: str) -> dict[int, dict[str, str]]:
        if name not in self._by_id:
            self._by_id[name] = {int(row["id"]): row for row in self.table(name)}
        return self._by_id[name]

    def names(self, table: str, id_column: str, language: int = FRENCH, column: str = "name") -> dict[int, str]:
        """Noms localisés d'une table `*_names` / `*_prose` : identifiant -> texte."""
        key = (table, id_column, language, column)
        if key not in self._names:
            self._names[key] = {
                int(row[id_column]): row[column]
                for row in self.table(table)
                if int(row["local_language_id"]) == language and row[column]
            }
        return self._names[key]


def optional_int(value: str) -> int | None:
    return int(value) if value else None


def value_at(past: list[tuple[int, int]], generation: int, current: int | None) -> int | None:
    """Valeur pour `generation` à partir d'un historique PokéAPI « jusqu'à la génération N : valeur »."""
    for until, value in sorted(past):
        if until >= generation:
            return value
    return current
