"""Planches de relecture de tous les lieux et niveaux DS, depuis les seules tuiles générées."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .maps_layout import identifier

_THUMBNAIL = 224
_CARD_HEIGHT = 280
_COLUMNS = 5
_ROWS = 5


@dataclass(frozen=True)
class ReviewCard:
    label: str
    folder: str
    size: tuple[int, int]
    levels: int
    box: tuple[int, int, int, int]


def write_review(maps: Path, output: Path) -> tuple[Path, ...]:
    output.mkdir(parents=True, exist_ok=True)
    cards = _cards(maps)
    sheets = []
    font = _review_font()
    for start in range(0, len(cards), _COLUMNS * _ROWS):
        sheet = Image.new("RGB", (_THUMBNAIL * _COLUMNS, _CARD_HEIGHT * _ROWS), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for index, card in enumerate(cards[start : start + _COLUMNS * _ROWS]):
            x, y = index % _COLUMNS * _THUMBNAIL, index // _COLUMNS * _CARD_HEIGHT
            image = region_thumbnail(maps / card.folder, card.size, card.levels, card.box)
            sheet.paste(image, (x, y))
            label = "\n".join(_label_lines(card.label, font))
            draw.multiline_text((x + 4, y + _THUMBNAIL + 2), label, fill="black", font=font)
        path = output / f"{maps.name}-{start // (_COLUMNS * _ROWS) + 1:02d}.png"
        sheet.save(path)
        sheets.append(path)
    fields = ("label", "folder", "size", "levels", "box")
    with (output / f"{maps.name}-index.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        writer.writerows((card.label, card.folder, card.size, card.levels, card.box) for card in cards)
    for path in output.glob(f"{maps.name}-[0-9][0-9].png"):
        if path not in sheets:
            path.unlink()
    return tuple(sheets)


def _review_font() -> ImageFont.FreeTypeFont:
    # La police intégrée à Pillow ne contient pas les accents français ni le tiret cadratin.
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    )
    font = next((path for path in candidates if path.is_file()), None)
    if font is None:
        raise ValueError("Relecture DS : installer Arial ou DejaVu Sans pour les libellés français")
    return ImageFont.truetype(str(font), 12)


def write_sprite_review(maps: Path, output: Path) -> Path:
    catalog = json.loads((maps / "sprites.json").read_text(encoding="utf-8"))
    sprites = catalog["sprites"]
    if not sprites or len(sprites) > 256:
        raise ValueError(f"{maps} : catalogue de PNJ invalide")
    output.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (96 * 12, 88 * math.ceil(len(sprites) / 12)), "#333344")
    draw = ImageDraw.Draw(sheet)
    font = _review_font()
    for index, sprite in enumerate(sprites):
        x, y = index % 12 * 96, index // 12 * 88
        with Image.open(maps / "sprites" / f"{sprite['graphics']}.webp") as source:
            image = source.convert("RGBA")
            image.thumbnail((32, 32), Image.Resampling.NEAREST)
            image = image.resize((image.width * 2, image.height * 2), Image.Resampling.NEAREST)
            sheet.alpha_composite(image, (x + (96 - image.width) // 2, y + 4))
        draw.text((x + 8, y + 69), str(sprite["graphics"]), fill="white", font=font)
    path = output / f"{maps.name}-sprites.png"
    sheet.convert("RGB").save(path)
    return path


def _label_lines(label: str, font: ImageFont.FreeTypeFont) -> tuple[str, ...]:
    lines, current = [], ""
    for character in label:
        if current and font.getlength(current + character) > _THUMBNAIL - 8:
            lines.append(current.rstrip())
            current = ""
        current += character
    if current:
        lines.append(current.rstrip())
    if len(lines) > 4:
        lines[3] = lines[3][:-2] + "…"
    return tuple(lines[:4])


def _cards(maps: Path) -> tuple[ReviewCard, ...]:
    with (maps / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    lookup = {row["const"]: row for row in rows}
    result = []
    for row in rows:
        parent = lookup[row["parent"]] if row["parent"] else row
        x, y, width, height = (int(row[key]) for key in ("x", "y", "width", "height"))
        result.append(
            ReviewCard(
                f"{row['number']} — {row['name_fr']}",
                identifier(parent["const"]),
                (int(parent["width"]), int(parent["height"])),
                int(parent["level_count"]),
                (x, y, x + width, y + height),
            )
        )
    metadata = json.loads((maps / "matrices.json").read_text(encoding="utf-8"))
    for display in metadata["displays"]:
        if not display["base"]:
            result.extend(_underground_cards(display))
            continue
        for source in display["blocks"]:
            if source["request"]["ceiling"] is None:
                continue
            name = lookup[display["base"]]["name_fr"]
            suffix = display["const"].rsplit("_LOWER", 1)[1].removeprefix("_") or "1"
            label = f"{name} — niveau inférieur {suffix}, bloc {source['request']['block']}"
            result.append(_block_card(display, source, label))
    return tuple(result)


def _underground_cards(display: dict) -> list[ReviewCard]:
    if display["const"] not in ("MAP_HEADER_UNDERGROUND", "MAP_UNDERGROUND"):
        return []
    seen = set()
    result = []
    for source in display["blocks"]:
        request = tuple(sorted(source["request"].items()))
        if request in seen:
            continue
        seen.add(request)
        label = f"Souterrain — bloc {source['request']['block']}"
        result.append(_block_card(display, source, label))
    return result


def _block_card(display: dict, source: dict, label: str) -> ReviewCard:
    left, top, right, bottom = source["bounds"]
    x0, y0 = display["bounds"][:2]
    box = (
        max(0, left - x0),
        max(0, top - y0),
        min(display["size"][0], right - x0),
        min(display["size"][1], bottom - y0),
    )
    return ReviewCard(label, identifier(display["const"]), tuple(display["size"]), display["level_count"], box)


def region_thumbnail(folder: Path, size: tuple[int, int], levels: int, box: tuple[int, int, int, int]) -> Image.Image:
    width, height = box[2] - box[0], box[3] - box[1]
    if min(width, height) <= 0 or max(size) > 32768:
        raise ValueError(f"{folder} : région de relecture invalide : {box}")
    reduction = max(0, math.ceil(math.log2(max(width, height) / _THUMBNAIL)))
    level = max(0, levels - 1 - reduction)
    factor = 2 ** (levels - 1 - level)
    left, top = box[0] // factor, box[1] // factor
    right, bottom = math.ceil(box[2] / factor), math.ceil(box[3] / factor)
    image = Image.new("RGBA", (right - left, bottom - top))
    for row in range(top // 256, math.ceil(bottom / 256)):
        for column in range(left // 256, math.ceil(right / 256)):
            path = folder / str(level) / f"{row}_{column}.webp"
            if path.is_file():
                with Image.open(path) as tile:
                    image.paste(tile, (column * 256 - left, row * 256 - top))
    image.thumbnail((_THUMBNAIL, _THUMBNAIL), Image.Resampling.NEAREST)
    background = Image.new("RGBA", (_THUMBNAIL, _THUMBNAIL), "#333344")
    background.alpha_composite(image, ((_THUMBNAIL - image.width) // 2, (_THUMBNAIL - image.height) // 2))
    return background.convert("RGB")
