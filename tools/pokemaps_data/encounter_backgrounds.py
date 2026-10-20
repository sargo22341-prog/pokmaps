"""Décors fixes des listes : métatuiles d’Émeraude, sans rendu de carte à l’exécution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .maps_render_gen3 import paint_metatile, tile_pixels
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_animation import animation_tiles
from .pret_gen3_tilesets import map_palettes
from .sources import fetch_pret


@dataclass(frozen=True)
class _Terrain:
    name: str
    secondary: str
    floor: int


TERRAINS = (
    _Terrain("grass", "gTileset_Petalburg", 0x001),
    _Terrain("tall_grass", "gTileset_Petalburg", 0x001),
    _Terrain("forest", "gTileset_Petalburg", 0x001),
    _Terrain("cave", "gTileset_Cave", 0x211),
    _Terrain("ice", "gTileset_Cave", 0x28F),
    _Terrain("sand", "gTileset_Cave", 0x276),
    _Terrain("floor", "gTileset_Petalburg", 0x014),
)


def _blocks(repo: Gen3PretRepo, secondary: str) -> dict[int, Image.Image]:
    primary, second = repo.tilesets["gTileset_General"], repo.tilesets[secondary]
    palettes = map_palettes(primary, second) + second.palettes[13:]
    pixels = dict.fromkeys(range(1024), bytes(64))
    pixels.update({i: tile_pixels(primary, i) for i in range(primary.tile_count)})
    pixels.update({512 + i: tile_pixels(second, i) for i in range(second.tile_count)})
    pixels.update(animation_tiles(repo, primary))
    pixels.update(animation_tiles(repo, second))
    return {
        index: paint_metatile(tile, pixels, palettes)
        for offset, source in ((0, primary), (512, second))
        for index, tile in enumerate(source.metatiles, offset)
    }


def _ground(terrain: _Terrain, blocks: dict[int, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (64, 64))
    for y in range(4):
        for x in range(4):
            number = terrain.floor
            if terrain.name == "tall_grass" and (x + y) % 3 == 0:
                number = 0x015
            image.paste(blocks[number], (16 * x, 16 * y))
    if terrain.name == "forest":
        for x, y in ((0, 0), (2, 2)):
            image.paste(blocks[0x01D], (16 * x, 16 * y))
    return image


def _lake(terrain: _Terrain, blocks: dict[int, Image.Image], grass: dict[int, Image.Image]) -> Image.Image:
    image = Image.new("RGB", (48, 48))
    numbers = ((0x0C8, 0x0C9, 0x0CA), (0x0D0, 0x0D1, 0x0D2), (0x0D8, 0x0D9, 0x0DA))
    green = set(grass[0x001].get_flattened_data())
    floor = blocks[terrain.floor]
    ice_shades = sorted(set(floor.get_flattened_data()), key=lambda rgb: sum(rgb))
    soil = sorted(
        set(grass[0x0C9].get_flattened_data()) - green - set(grass[0x0D1].get_flattened_data()),
        key=lambda rgb: sum(rgb),
    )
    for row, numbers_row in enumerate(numbers):
        for column, number in enumerate(numbers_row):
            tile = grass[number].copy()
            if terrain.name not in {"grass", "tall_grass", "forest"}:
                for y in range(16):
                    for x in range(16):
                        color = tile.getpixel((x, y))
                        if color in green:
                            tile.putpixel((x, y), floor.getpixel((x, y)))
                        elif terrain.name == "ice" and color in soil:
                            tile.putpixel((x, y), ice_shades[soil.index(color) * (len(ice_shades) - 1) // len(soil)])
            image.paste(tile, (column * 16, row * 16))
    return image


def build_encounter_backgrounds(cache: Path, assets: Path) -> None:
    repo = Gen3PretRepo(fetch_pret(cache, "pokeemerald"), (("emerald", "EMERALD"),))
    blocks = {secondary: _blocks(repo, secondary) for secondary in {terrain.secondary for terrain in TERRAINS}}
    output = assets / "encounter_backgrounds"
    output.mkdir(parents=True, exist_ok=True)
    grass = blocks["gTileset_Petalburg"]
    for terrain in TERRAINS:
        images = {
            "ground": _ground(terrain, blocks[terrain.secondary]),
            "lake": _lake(terrain, blocks[terrain.secondary], grass),
        }
        for kind, image in images.items():
            target = output / f"{terrain.name}_{kind}.webp"
            image.save(target, "WEBP", lossless=True, exact=True)
            with Image.open(target) as written:
                if written.convert("RGB").tobytes() != image.tobytes():
                    raise ValueError(f"{target} : conversion sans perte incohérente")
    validate_encounter_backgrounds(assets)


def validate_encounter_backgrounds(assets: Path) -> None:
    for terrain in TERRAINS:
        for kind, size in (("ground", (64, 64)), ("lake", (48, 48))):
            path = assets / "encounter_backgrounds" / f"{terrain.name}_{kind}.webp"
            with Image.open(path) as image:
                if image.format != "WEBP" or image.size != size or image.mode != "RGB":
                    raise ValueError(f"{path} : texture fixe {size} RGB WebP attendue")
