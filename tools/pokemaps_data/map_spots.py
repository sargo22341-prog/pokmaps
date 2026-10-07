"""Emplacements de Pokémon sauvages retouchés à la main (tools/data/map_spots.csv).

Une ligne par emplacement ; une ligne sans coordonnées marque un terrain volontairement vide. Un terrain présent
dans le fichier remplace celui que la génération calcule, pour tous les jeux de sa famille de cartes
(games.Game.map_family). Le fichier est lu par la génération et lu puis réécrit par tools/map_editor.py.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .games import map_families

SPOTS_CSV = Path(__file__).resolve().parents[1] / "data/map_spots.csv"
SPOT_KINDS = ("grass", "water", "floor")
_HEADER = ("family", "map_identifier", "kind", "x", "y")

Point = tuple[int, int]


@dataclass(frozen=True, order=True)
class TerrainKey:
    """Un terrain d'une carte : herbes (grass), eau (water) ou sol (floor)."""

    family: str
    map_identifier: str
    kind: str


def read_spots(path: Path = SPOTS_CSV) -> dict[TerrainKey, frozenset[Point]]:
    """Lit et valide le fichier ; une erreur nomme la ligne fautive."""
    if not path.is_file():
        return {}
    grouped: dict[TerrainKey, set[Point]] = {}
    empty: set[TerrainKey] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != _HEADER:
            raise ValueError(f"{path.name} : en-tête attendu {','.join(_HEADER)}")
        for line, row in enumerate(reader, start=2):
            key, point = _parse_row(row, f"{path.name}:{line}")
            points = grouped.setdefault(key, set())
            if point is None:
                empty.add(key)
            elif point in points:
                raise ValueError(f"{path.name}:{line} : emplacement en double {point}")
            else:
                points.add(point)
    if mixed := sorted(key for key in empty if grouped[key]):
        raise ValueError(f"{path.name} : terrains à la fois vides et remplis : {mixed}")
    return {key: frozenset(points) for key, points in grouped.items()}


def write_spots(spots: Mapping[TerrainKey, Iterable[Point]], path: Path = SPOTS_CSV) -> None:
    """Réécrit tout le fichier, trié, via un fichier temporaire pour ne jamais le laisser à moitié écrit."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(_HEADER)
        for key in sorted(spots):
            points = sorted(spots[key])
            prefix = (key.family, key.map_identifier, key.kind)
            if points:
                writer.writerows((*prefix, x, y) for x, y in points)
            else:
                writer.writerow((*prefix, "", ""))
    os.replace(temporary, path)


def _parse_row(row: dict[str, str], where: str) -> tuple[TerrainKey, Point | None]:
    family, kind = row["family"], row["kind"]
    if family not in map_families():
        raise ValueError(f"{where} : famille de cartes inconnue {family!r}")
    if kind not in SPOT_KINDS:
        raise ValueError(f"{where} : terrain inconnu {kind!r}")
    if not row["map_identifier"]:
        raise ValueError(f"{where} : carte manquante")
    key = TerrainKey(family, row["map_identifier"], kind)
    if not row["x"] and not row["y"]:
        return key, None
    try:
        return key, (int(row["x"]), int(row["y"]))
    except ValueError as error:
        raise ValueError(f"{where} : coordonnées invalides ({row['x']!r}, {row['y']!r})") from error
