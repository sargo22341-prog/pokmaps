"""Surfaces aquatiques relues dans le rendu HGSS lorsque le BDHC est décalé."""

import csv
from pathlib import Path

from PIL import Image

from .sources import DATA_DIR


def read_water_regions(path: Path = DATA_DIR / "hgss_water_regions.csv") -> dict[int, list[tuple[int, ...]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["header", "left", "top", "right", "bottom", "reason"]:
            raise ValueError(f"{path} : colonnes des surfaces aquatiques invalides")
        result: dict[int, list[tuple[int, ...]]] = {}
        for line, row in enumerate(reader, 2):
            header, left, top, right, bottom = (int(row[key]) for key in reader.fieldnames[:-1])
            if not 0 <= header < 540 or not row["reason"].strip():
                raise ValueError(f"{path}:{line} : surface aquatique sans carte ni justification")
            if not (0 <= left < right <= 32768 and 0 <= top < bottom <= 32768):
                raise ValueError(f"{path}:{line} : rectangle aquatique invalide")
            regions = result.setdefault(header, [])
            bounds = left, top, right, bottom
            if bounds in regions or sum(len(v) for v in result.values()) >= 128:
                raise ValueError(f"{path}:{line} : rectangle répété ou trop de surfaces aquatiques")
            regions.append(bounds)
    return result


def water_points(path: Path, regions: list[tuple[int, ...]]) -> list[tuple[int, int]]:
    points = set()
    with Image.open(path) as source:
        image = source.convert("RGBA")
        for left, top, right, bottom in regions:
            if right > image.width or bottom > image.height or (right - left) * (bottom - top) > 1024 * 1024:
                raise ValueError(f"{path} : surface aquatique hors image ou trop grande")
            candidates = {
                (x, y)
                for y in range(top, bottom, 16)
                for x in range(left, right, 16)
                if _water_neighborhood(image, x, y)
            }
            if not candidates:
                raise ValueError(f"{path} : aucune eau visible dans {(left, top, right, bottom)}")
            points.update(candidates)
    return sorted(points)


def _water_neighborhood(image: Image.Image, x: int, y: int) -> bool:
    if x < 8 or y < 8 or x + 8 >= image.width or y + 8 >= image.height:
        return False
    for dx in (-8, 0, 8):
        for dy in (-8, 0, 8):
            red, green, blue, alpha = image.getpixel((x + dx, y + dy))
            if alpha != 255 or blue <= green + 10 or green <= red + 15 or blue <= red + 40:
                return False
    return True
