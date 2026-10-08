"""Emplacements de Pokémon sauvages retouchés à la main (tools/data/map_spots.csv).

Une ligne par emplacement ; une ligne sans coordonnées marque un terrain volontairement vide. Un terrain présent
dans le fichier remplace celui que la génération calcule, pour sa famille de cartes ou uniquement son groupe
de versions. Une retouche propre à un groupe prime sur celle de la famille pour ce terrain.
Le fichier est lu par la génération et lu puis réécrit par tools/map_editor.py.
"""

from __future__ import annotations

import csv
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .games import map_families

SPOTS_CSV = Path(__file__).resolve().parents[1] / "data/map_spots.csv"
SPOT_KINDS = ("grass", "water", "floor", "tree", "rock")
_HEADER = ("family", "map_identifier", "kind", "x", "y")
_SCOPED_HEADER = (*_HEADER, "version_group")

Point = tuple[int, int]


@dataclass(frozen=True, order=True)
class TerrainKey:
    """Un terrain d'une carte : herbes (grass), eau (water), sol (floor), arbres (tree) ou rochers (rock)."""

    family: str
    map_identifier: str
    kind: str
    version_group: str = ""


def selected_key(spots: Mapping[TerrainKey, object], key: TerrainKey, version_group: str) -> TerrainKey:
    """La retouche propre au groupe prime sur la retouche commune de la famille."""
    specific = TerrainKey(key.family, key.map_identifier, key.kind, version_group)
    return specific if specific in spots else TerrainKey(key.family, key.map_identifier, key.kind)


def read_spots(path: Path = SPOTS_CSV) -> dict[TerrainKey, frozenset[Point]]:
    """Lit et valide le fichier ; une erreur nomme la ligne fautive."""
    if not path.is_file():
        return {}
    grouped: dict[TerrainKey, set[Point]] = {}
    empty: set[TerrainKey] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) not in (_HEADER, _SCOPED_HEADER):
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
        scoped = any(key.version_group for key in spots)
        writer.writerow(_SCOPED_HEADER if scoped else _HEADER)
        for key in sorted(spots):
            points = sorted(spots[key])
            prefix = (key.family, key.map_identifier, key.kind)
            suffix = (key.version_group,) if scoped else ()
            if points:
                writer.writerows((*prefix, x, y, *suffix) for x, y in points)
            else:
                writer.writerow((*prefix, "", "", *suffix))
    os.replace(temporary, path)


def _parse_row(row: dict[str, str], where: str) -> tuple[TerrainKey, Point | None]:
    if None in row or any(value is None for value in row.values()):
        raise ValueError(f"{where} : nombre de colonnes invalide")
    family, kind = row["family"], row["kind"]
    if family not in map_families():
        raise ValueError(f"{where} : famille de cartes inconnue {family!r}")
    if kind not in SPOT_KINDS:
        raise ValueError(f"{where} : terrain inconnu {kind!r}")
    if not row["map_identifier"]:
        raise ValueError(f"{where} : carte manquante")
    group = row.get("version_group", "")
    if group and group not in map_families()[family]:
        raise ValueError(f"{where} : groupe de versions incompatible avec la famille {group!r}")
    key = TerrainKey(family, row["map_identifier"], kind, group)
    if not row["x"] and not row["y"]:
        return key, None
    try:
        return key, (int(row["x"]), int(row["y"]))
    except ValueError as error:
        raise ValueError(f"{where} : coordonnées invalides ({row['x']!r}, {row['y']!r})") from error
