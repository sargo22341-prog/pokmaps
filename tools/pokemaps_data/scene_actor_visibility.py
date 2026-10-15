"""Figurants masqués sur la carte, sans retirer les données de leurs scripts."""

from __future__ import annotations

import csv
from pathlib import Path

from .sources import DATA_DIR

_FAMILIES = frozenset({"ruby-sapphire-emerald", "firered-leafgreen"})


def read_scene_actor_visibility(
    path: Path = DATA_DIR / "scene_actor_visibility.csv",
) -> frozenset[tuple[str, str]]:
    if path.stat().st_size > 64 * 1024:
        raise ValueError(f"{path.name} : fichier trop volumineux")
    actors: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["family", "text", "reason"]:
            raise ValueError(f"{path.name} : colonnes incorrectes")
        for line, row in enumerate(reader, 2):
            if len(row) != 3 or any(value is None for value in row.values()):
                raise ValueError(f"{path.name}:{line} : ligne incomplète ou colonnes en trop")
            key = (row["family"], row["text"])
            if line > 257 or key[0] not in _FAMILIES or ":" not in key[1] or not row["reason"].strip():
                raise ValueError(f"{path.name}:{line} : figurant ou justification incorrects : {key}")
            if key in actors:
                raise ValueError(f"{path.name}:{line} : figurant répété : {key}")
            actors.add(key)
    return frozenset(actors)
