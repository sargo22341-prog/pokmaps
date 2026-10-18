"""Provenance des cartes événementielles, portée comme donnée jusqu'à l'application."""

import csv
from functools import lru_cache

from .sources import DATA_DIR


@lru_cache(maxsize=1)
def _maps() -> tuple[tuple[str, str], ...]:
    with (DATA_DIR / "external_event_maps.csv").open(encoding="utf-8", newline="") as source:
        rows = tuple((row["key"], row["entrance"]) for row in csv.DictReader(source))
    if len({key for key, _ in rows}) != len(rows) or any(not key or not entrance for key, entrance in rows):
        raise ValueError("external_event_maps.csv : clé répétée, clé vide ou entrée vide")
    return rows


def event_map(identifier: str) -> tuple[str | None, int]:
    identifier = identifier.removeprefix("header-")
    matches = [
        (key, position if identifier in {key, entrance} else 0)
        for position, (key, entrance) in enumerate(_maps(), 1)
        if identifier == key or identifier.startswith(f"{key}-")
    ]
    if len(matches) > 1:
        raise ValueError(f"external_event_maps.csv : plusieurs événements pour {identifier}")
    return matches[0] if matches else (None, 0)


def event_locations() -> frozenset[str]:
    return frozenset(key for key, _ in _maps())
