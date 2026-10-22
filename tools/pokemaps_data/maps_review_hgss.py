"""Planches indexées des lieux et assemblages Johto, avec repères des passages natifs."""

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from .maps_review_gen4 import _label_lines, _review_font, region_thumbnail
from .preview_johto_hgss import validate_johto_output

_COLUMNS = 4
_PAGE_SIZE = 16
_CARD_WIDTH = 288
_CARD_HEIGHT = 352


def write_johto_review(maps: Path, output: Path) -> tuple[Path, ...]:
    catalog = json.loads((maps / "catalog.json").read_text(encoding="utf-8"))
    validate_johto_output(maps, catalog)
    output.mkdir(parents=True, exist_ok=True)
    offsets = {part["header"]: part["offset"] for plan in catalog["plans"] for part in plan["parts"]}
    cards = []
    for record in catalog["maps"]:
        warps = [
            (p["index"], tuple(p["source_pixel"][k] - offsets[record["header"]][k] for k in (0, 1)))
            for p in catalog["passages"]
            if p["source"] == record["header"]
        ]
        cards.append(
            {"kind": "lieu", "label": f"{record['header']} — {record['name_fr']}", "record": record, "warps": warps}
        )
    for plan in catalog["plans"]:
        label = plan["name_fr"]
        cards.append({"kind": "plan", "label": f"{label} — assemblage ({len(plan['parts'])} lieux)", "record": plan})
    pages = []
    index = []
    for start in range(0, len(cards), _PAGE_SIZE):
        path = output / f"johto-{len(pages) + 1:02d}.png"
        _sheet(maps, cards[start : start + _PAGE_SIZE], path)
        pages.append(path)
        for card in cards[start : start + _PAGE_SIZE]:
            index.append(
                {
                    "sheet": path.name,
                    "label": card["label"],
                    "kind": card["kind"],
                    "id": card["record"].get("header", card["record"].get("id")),
                }
            )
    world = next((plan for plan in catalog["plans"] if plan["layout"] == "native"), None)
    if world is not None:
        detail = output / "johto-exterieurs-detail.png"
        _world_sheet(maps, world, detail)
        pages.append(detail)
        index.append({"sheet": detail.name, "label": world["name_fr"], "kind": "plan-detail", "id": world["id"]})
    report = {
        "commit": catalog["commit"],
        "catalog_sha256": hashlib.sha256((maps / "catalog.json").read_bytes()).hexdigest(),
        "cards": index,
        "sheets": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in pages},
    }
    (output / "index.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return tuple(pages)


def _sheet(maps: Path, cards: list[dict], path: Path) -> None:
    sheet = Image.new("RGB", (_COLUMNS * _CARD_WIDTH, 4 * _CARD_HEIGHT), "#e6e6e6")
    draw = ImageDraw.Draw(sheet)
    font = _review_font()
    for index, card in enumerate(cards):
        x, y = index % _COLUMNS * _CARD_WIDTH, index // _COLUMNS * _CARD_HEIGHT
        record = card["record"]
        if card["kind"] == "lieu":
            with Image.open(maps / record["image"]) as source:
                image = source.convert("RGBA")
                markers = ImageDraw.Draw(image)
                for number, (px, py) in card["warps"]:
                    markers.ellipse((px - 5, py - 5, px + 5, py + 5), outline="cyan", width=2)
                    markers.text((px + 7, py), str(number), fill="cyan", font=font, stroke_width=1, stroke_fill="black")
                image = image.crop(image.getbbox())
        else:
            image = region_thumbnail(
                maps / "plans" / record["id"], tuple(record["size"]), record["level_count"], (0, 0, *record["size"])
            ).convert("RGBA")
        image.thumbnail((_CARD_WIDTH - 16, _CARD_WIDTH - 16), Image.Resampling.NEAREST)
        sheet.paste(image, (x + (_CARD_WIDTH - image.width) // 2, y + 4), image)
        label = "\n".join(_label_lines(card["label"], font))
        draw.multiline_text((x + 8, y + _CARD_WIDTH), label, fill="black", font=font)
    sheet.save(path)


def _world_sheet(maps: Path, plan: dict, output: Path) -> None:
    reduction = max(0, math.ceil(math.log2(max(plan["size"]) / 1600)))
    level = max(0, plan["level_count"] - 1 - reduction)
    factor = 2 ** (plan["level_count"] - 1 - level)
    size = tuple(math.ceil(side / factor) for side in plan["size"])
    image = Image.new("RGBA", size, "#303041")
    for row in range(math.ceil(size[1] / 256)):
        for column in range(math.ceil(size[0] / 256)):
            path = maps / "plans" / plan["id"] / str(level) / f"{row}_{column}.webp"
            if path.is_file():
                with Image.open(path) as tile:
                    image.alpha_composite(tile.convert("RGBA"), (column * 256, row * 256))
    image.convert("RGB").save(output)
