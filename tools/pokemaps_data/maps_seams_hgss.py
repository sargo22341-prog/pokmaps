"""Raccords extérieurs HGSS : profondeur commune aux décors des lieux voisins."""

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops

from .maps_raster_gen4 import RasterCanvas
from .maps_render_hgss import HgssRenderer, camera_cotangent


def overlapping_tiles(root: Path, records: list[dict], parts: list[dict]) -> set[tuple[int, int]]:
    coverage: dict[tuple[int, int], Image.Image] = {}
    overlaps = set()
    for record, part in zip(records, parts, strict=True):
        x, y = part["offset"]
        with Image.open(root / record["image"]) as source:
            alpha = source.convert("RGBA").getchannel("A").point(lambda value: 255 if value else 0)
            for row in range(y // 256, (y + source.height + 255) // 256):
                for column in range(x // 256, (x + source.width + 255) // 256):
                    left, top = column * 256 - x, row * 256 - y
                    mask = alpha.crop((left, top, left + 256, top + 256))
                    if mask.getbbox() is None:
                        continue
                    key = row, column
                    previous = coverage.get(key)
                    if previous is not None:
                        if ImageChops.multiply(previous, mask).getbbox() is not None:
                            overlaps.add(key)
                        mask = ImageChops.lighter(previous, mask)
                    coverage[key] = mask
    return overlaps


def render_seams(root: Path, records: list[dict], parts: list[dict], renderer: HgssRenderer, output: Path) -> None:
    origin = tuple(min(record["origin_pixels"][axis] for record in records) for axis in (0, 1))

    @lru_cache(maxsize=8)
    def geometry(header_index: int) -> tuple:
        header = renderer.repo.headers[header_index]
        return tuple(
            (x, z, renderer.triangles(header, block, altitude))
            for x, z, block, altitude in renderer.repo.blocks(header)
        )

    tiles = overlapping_tiles(root, records, parts)
    for index, (row, column) in enumerate(sorted(tiles)):
        frame = origin[0] + column * 256, origin[1] + row * 256
        candidates = [record for record in records if _intersects(record, frame)]
        angles = {camera_cotangent(renderer.repo.root, renderer.repo.headers[r["header"]]) for r in candidates}
        if len(angles) != 1:
            raise ValueError(f"HGSS : caméras incompatibles au raccord {frame} : {angles}")
        canvas = RasterCanvas(frame, (256, 256), angles.pop())
        for translucent in (False, True):
            for record in candidates:
                for x, z, triangles in geometry(record["header"]):
                    for vertices, material in triangles:
                        if (material.alpha < 31) == translucent:
                            canvas.triangle(vertices, material, (x * 512, z * 512))
        canvas.image().save(output / f"{row}_{column}.webp", "WEBP", lossless=True, method=4)
        if index % 50 == 0:
            print(f"  Raccords {records[0]['plan']} : {index + 1}/{len(tiles)}", flush=True)


def _intersects(record: dict, frame: tuple[int, int]) -> bool:
    x, y = record["origin_pixels"]
    width, height = record["size"]
    return x < frame[0] + 256 and y < frame[1] + 256 and x + width > frame[0] and y + height > frame[1]
