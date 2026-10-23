"""Rejet des points HGSS masqués par une carte voisine dans le plan extérieur final."""

from pathlib import Path

from PIL import Image


def visible_world_cells(root: Path, record: dict, cells: dict, plan: dict, offset: list[int], rejected: list) -> dict:
    if plan["layout"] != "native":
        return cells
    tiles: dict[tuple[int, int], Image.Image] = {}
    result = {}
    with Image.open(root / record["image"]) as source:
        native = source.convert("RGBA")
        for kind, points in cells.items():
            accepted = []
            for x, y in points:
                world_x, world_y = x + offset[0], y + offset[1]
                key = world_y // 256, world_x // 256
                if key not in tiles:
                    if len(tiles) >= 256:
                        raise ValueError(f"{record['const']} : plus de 256 tuiles de placement extérieur")
                    path = root / "plans" / plan["id"] / str(plan["level_count"] - 1) / f"{key[0]}_{key[1]}.webp"
                    with Image.open(path) as image:
                        tiles[key] = image.convert("RGBA")
                if native.getpixel((x, y)) == tiles[key].getpixel((world_x % 256, world_y % 256)):
                    accepted.append((x, y))
                else:
                    rejected.append(dict(point=(x, y), kind=kind, reason="décor masqué dans le plan extérieur final"))
            if accepted:
                result[kind] = accepted
    return result
