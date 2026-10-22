#!/usr/bin/env python3
"""Planches de relecture des placements HGSS, sans modifier les points éditoriaux."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from pokemaps_data.map_spots import TerrainKey, read_spots, selected_key
from pokemaps_data.maps_review_gen4 import _review_font
from pokemaps_data.placement_hgss import FAMILY
from pokemaps_data.preview_placement_hgss import check_placement

ROOT = Path(__file__).resolve().parent
COLORS = {"grass": "#00ff00", "floor": "#ff8800", "water": "#00bfff", "tree": "#ff00ff", "rock": "#ff0000"}


def review(assets: Path, output: Path) -> None:
    data = check_placement(assets)
    spots = read_spots()
    output.mkdir(parents=True, exist_ok=True)
    font = _review_font().font_variant(size=16)
    records = data["catalog"]["maps"]
    index = []
    for start in range(0, len(records), 12):
        sheet = Image.new("RGB", (1280, 1200), "#eeeeee")
        for cell, record in enumerate(records[start : start + 12]):
            image = _marked(assets, record, spots)
            image.save(output / f"{record['header']}.png")
            image.thumbnail((320, 340), Image.Resampling.LANCZOS)
            x, y = cell % 4 * 320, cell // 4 * 400
            sheet.paste(image, (x + (320 - image.width) // 2, y + 55))
            draw = ImageDraw.Draw(sheet)
            draw.text((x + 4, y + 4), f"{record['header']} · {record['scope']}", font=font, fill="black")
            draw.text((x + 4, y + 25), record["name_fr"][:35], font=font, fill="black")
            index.append(dict(header=record["header"], map=record["identifier"], sheet=start // 12 + 1))
        sheet.save(output / f"sheet-{start // 12 + 1:02d}.jpg", quality=92)
    (output / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(records)} lieux sur {len(range(0, len(records), 12))} planches : {output}")


def _marked(assets: Path, record: dict, spots: dict) -> Image.Image:
    with Image.open(assets.parent / "hgss-maps/atlas" / record["image"]) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    for kind in record["terrain"]:
        key = selected_key(spots, TerrainKey(FAMILY, record["identifier"], kind), FAMILY)
        for x, y in spots.get(key, ()):
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=COLORS[kind], outline="black", width=1)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ROOT / "build/preview/hgss-placement")
    parser.add_argument("--output", type=Path, default=ROOT / "build/scratchpad/hgss-placement-review")
    args = parser.parse_args()
    review(args.assets, args.output)


if __name__ == "__main__":
    main()
