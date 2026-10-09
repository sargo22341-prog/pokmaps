"""Pixels GBA vérifiés indépendamment du rendu des sources complètes."""

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.maps_render_gen3 import paint_metatile, tile_pixels
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_animation import animation_tiles
from pokemaps_data.pret_gen3_tilesets import Gen3Metatile, Gen3Tileset


def _tileset() -> Gen3Tileset:
    pixels = bytes([1] * 8 + [2] * 8 + [3] * 8 + [4] * 8)
    palettes = tuple(tuple((i * 10, p * 10, 0) for i in range(16)) for p in range(16))
    return Gen3Tileset("gTileset_Test", False, 4, pixels * 8, 32, palettes, (), 512, 512, 6, True, "NULL")


def test_tile_numbers_follow_rows_of_eight_pixel_tiles() -> None:
    tileset = _tileset()
    assert tile_pixels(tileset, 0) == bytes([1] * 64)
    assert tile_pixels(tileset, 3) == bytes([4] * 64)
    with pytest.raises(ValueError, match="tuile absente"):
        tile_pixels(tileset, 4)


@pytest.mark.parametrize(("flip", "point"), [(0, (0, 0)), (0x400, (7, 0)), (0x800, (0, 7)), (0xC00, (7, 7))])
def test_descriptors_apply_both_flips_and_palette(flip: int, point: tuple[int, int]) -> None:
    pixels = {0: bytes(64), 1: bytes([1] + [0] * 63)}
    tile = Gen3Metatile((0x2001 | flip, 0, 0, 0, 0, 0, 0, 0), 0, 1, None, None)
    image = paint_metatile(tile, pixels, _tileset().palettes)
    assert image.getpixel(point) == (10, 20, 0)
    assert sum(image.getpixel((x, y)) == (10, 20, 0) for y in range(16) for x in range(16)) == 1


@pytest.mark.parametrize("layer", [0, 1, 2])
def test_top_color_zero_reveals_the_bottom_layer(layer: int) -> None:
    pixels = {0: bytes(64), 1: bytes([2] * 64), 2: bytes([3] + [0] * 63), 20: bytes([4] * 64)}
    tile = Gen3Metatile((1, 1, 1, 1, 2, 0, 0, 0), 0, layer, None, None)
    image = paint_metatile(tile, pixels, _tileset().palettes)
    assert image.getpixel((0, 0)) == (30, 0, 0)
    assert image.getpixel((1, 0)) == (20, 0, 0)
    assert image.getpixel((15, 15)) == (20, 0, 0)


def test_normal_layer_has_the_engine_background_tile() -> None:
    tile = Gen3Metatile((0,) * 8, 0, 0, None, None)
    image = paint_metatile(tile, {0: bytes(64), 20: bytes([5] * 64)}, _tileset().palettes)
    assert image.getpixel((8, 8)) == (50, 30, 0)


def test_unknown_descriptor_or_layer_fails() -> None:
    tile = Gen3Metatile((1,) * 8, 0, 1, None, None)
    with pytest.raises(ValueError, match="Descripteur GBA invalide"):
        paint_metatile(tile, {}, _tileset().palettes)
    with pytest.raises(ValueError, match="Couche GBA inconnue"):
        paint_metatile(replace(tile, layer_type=3), {}, _tileset().palettes)


@pytest.mark.parametrize("ruby", [False, True])
def test_animation_uses_first_table_entry_and_vram_addresses(tmp_path: Path, ruby: bool) -> None:
    directory = tmp_path / "src"
    directory.mkdir()
    (tmp_path / "graphics").mkdir()
    for name, shade in (("first", 7), ("second", 9)):
        image = Image.new("P", (8, 8), shade)
        image.putpalette([value for index in range(256) for value in (index, index, index)])
        image.save(tmp_path / f"graphics/{name}.png")
    declarations = 'const u16 gFrame0[] = INCBIN_U16("graphics/first.4bpp");\n'
    declarations += 'const u16 gFrame1[] = INCBIN_U16("graphics/second.4bpp");\n'
    declarations += "const u16 *const gFrames[] = {gFrame0, gFrame1};\n"
    if ruby:
        body = "QueueTilesetAnimDma(gFrames[i], BG_TILE_ADDR(2), 0x20);"
        versions = (("ruby", "RUBY"), ("sapphire", "SAPPHIRE"))
    else:
        body = "AppendTilesetAnimToBuffer(gFrames[i], (u16 *)(BG_VRAM + TILE_OFFSET_4BPP(8)), 1 * TILE_SIZE_4BPP);"
        versions = (("emerald", "EMERALD"),)
    text = declarations + "void Init(void) { sCallback = Tick; }\nvoid Tick(u16 i) { " + body + " }"
    path = directory / ("tileset_anim.c" if ruby else "tileset_anims.c")
    path.write_text(text, encoding="utf-8")
    repo = Gen3PretRepo(tmp_path, versions)
    assert animation_tiles(repo, replace(_tileset(), animation_callback="Init")) == {8: bytes([7] * 64)}
    path.write_text(text.replace("gFrames[i]", "unsupported"), encoding="utf-8")
    with pytest.raises(ValueError, match="non pris en charge"):
        animation_tiles(repo, replace(_tileset(), animation_callback="Init"))
