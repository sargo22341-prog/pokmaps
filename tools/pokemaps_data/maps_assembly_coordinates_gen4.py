"""Repères natifs conservés avec les plans DS assemblés, pour le terrain et l'éditeur."""

from __future__ import annotations

import json
from pathlib import Path

from .maps_layout import identifier


def read_coordinates(folder: Path) -> dict[str, tuple[str, tuple[int, int]]]:
    path = folder / "assemblies.json"
    if not path.is_file():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, dict) or len(rows) > 1000:
        raise ValueError(f"{path} : coordonnées d'assemblage invalides")
    result = {}
    for const, row in rows.items():
        if not isinstance(row, dict) or set(row) != {"native", "offset"}:
            raise ValueError(f"{path} : repère invalide pour {const}")
        offset = row["offset"]
        if not isinstance(row["native"], str) or not row["native"] or not isinstance(offset, list) or len(offset) != 2:
            raise ValueError(f"{path} : repère incomplet pour {const}")
        if any(type(value) is not int or not 0 <= value <= 8192 for value in offset):
            raise ValueError(f"{path} : translation invalide pour {const}")
        result[const] = (row["native"], (offset[0], offset[1]))
    return result


def editor_offsets(maps: Path) -> dict[tuple[str, str], tuple[int, int]]:
    return {
        (family, identifier(const)): offset
        for family in ("platinum", "diamond-pearl")
        for const, (_, offset) in read_coordinates(maps / family).items()
    }
