"""Assemblages HGSS tuilés : matrice native dehors, atlas de salles séparées à l'intérieur."""

import math
from pathlib import Path

from PIL import Image

from .maps_render import level_count
from .maps_render_hgss import HgssRenderer


def plan_layout(records: list[dict]) -> tuple[tuple[int, int], list[dict]]:
    if not records or len(records) > 256:
        raise ValueError("HGSS : plan vide ou contenant plus de 256 lieux")
    native = records[0]["plan"] in ("johto-exterieurs", "kanto-exterieurs")
    if native:
        origin = tuple(min(record["origin_pixels"][axis] for record in records) for axis in (0, 1))
        positions = [tuple(record["origin_pixels"][axis] - origin[axis] for axis in (0, 1)) for record in records]
    else:
        columns = min(4, math.ceil(math.sqrt(len(records))))
        cell = tuple(max(record["size"][axis] for record in records) + 256 for axis in (0, 1))
        positions = [(index % columns * cell[0], index // columns * cell[1]) for index in range(len(records))]
    parts = [
        {"header": record["header"], "offset": position} for record, position in zip(records, positions, strict=True)
    ]
    size = tuple(
        max(position[axis] + record["size"][axis] for record, position in zip(records, positions, strict=True))
        for axis in (0, 1)
    )
    if max(size) > 32768:
        raise ValueError(f"HGSS : plan trop grand : {size}")
    return size, parts


def write_plan(root: Path, records: list[dict], output: Path, renderer: HgssRenderer | None = None) -> dict:
    size, parts = plan_layout(records)
    levels = level_count(*size)
    output.mkdir(parents=True)
    for record, part in zip(records, parts, strict=True):
        with Image.open(root / record["image"]) as image:
            _paste_tiles(image.convert("RGBA"), tuple(part["offset"]), output / str(levels - 1))
    if renderer is not None and records[0]["plan"] in ("johto-exterieurs", "kanto-exterieurs"):
        from .maps_seams_hgss import render_seams

        render_seams(root, records, parts, renderer, output / str(levels - 1))
    for level in range(levels - 2, -1, -1):
        _reduce_tiles(output / str(level + 1), output / str(level))
    return {
        "id": records[0]["plan"],
        "name_fr": _plan_name(records),
        "size": size,
        "level_count": levels,
        "parts": parts,
        "layout": "native" if records[0]["plan"] in ("johto-exterieurs", "kanto-exterieurs") else "atlas",
    }


def _plan_name(records: list[dict]) -> str:
    if records[0]["plan"] == "johto-exterieurs":
        return "Johto — extérieurs"
    if records[0]["plan"] == "kanto-exterieurs":
        return "Kanto — extérieurs"
    if len(records) == 1:
        return records[0]["name_fr"]
    place = records[0]["name_fr"].split(" — ", 1)[0]
    floor = records[0]["floor"]
    if floor == "base":
        return f"{place} — salles et annexes"
    if floor.startswith("b"):
        return f"{place} — salles du sous-sol {int(floor[1:-1])}"
    number = int(floor[:-1]) - 1
    suffix = "rez-de-chaussée" if number == 0 else ("1er étage" if number == 1 else f"{number}e étage")
    return f"{place} — salles du {suffix}"


def _paste_tiles(image: Image.Image, offset: tuple[int, int], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    x, y = offset
    for row in range(y // 256, math.ceil((y + image.height) / 256)):
        for column in range(x // 256, math.ceil((x + image.width) / 256)):
            left, top = column * 256 - x, row * 256 - y
            fragment = image.crop((left, top, left + 256, top + 256))
            if fragment.getextrema()[3][1] == 0:
                continue
            path = output / f"{row}_{column}.webp"
            if path.is_file():
                with Image.open(path) as previous:
                    fragment = Image.alpha_composite(previous.convert("RGBA"), fragment)
            fragment.save(path, "WEBP", lossless=True, method=4)


def _reduce_tiles(source: Path, output: Path) -> None:
    positions = [tuple(map(int, path.stem.split("_"))) for path in source.glob("*.webp")]
    if len(positions) > 16384:
        raise ValueError(f"{source} : trop de tuiles HGSS")
    output.mkdir()
    for row, column in sorted({(row // 2, column // 2) for row, column in positions}):
        image = Image.new("RGBA", (512, 512))
        for dy in (0, 1):
            for dx in (0, 1):
                path = source / f"{row * 2 + dy}_{column * 2 + dx}.webp"
                if path.is_file():
                    with Image.open(path) as tile:
                        image.paste(tile, (dx * 256, dy * 256))
        image.resize((256, 256), Image.Resampling.BOX).save(output / f"{row}_{column}.webp", "WEBP", lossless=True)
