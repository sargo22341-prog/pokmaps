"""Pixels 4 bpp, palettes et attributs u16/u32 des trois variantes de tilesets."""

import struct
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_tilesets import map_palettes, read_palette, read_tilesets
from pokemaps_data.sources import pret_dir


@pytest.fixture
def tileset_repo(tmp_path: Path) -> Path:
    directory = tmp_path / "data/tilesets/primary/general"
    (directory / "palettes").mkdir(parents=True)
    image = Image.new("P", (8, 8), 3)
    image.putpalette([value for index in range(256) for value in (index, index, index)])
    image.save(directory / "tiles.png")
    palette = "JASC-PAL\n0100\n16\n" + "248 128 0\n" * 16
    for index in range(16):
        (directory / f"palettes/{index:02d}.pal").write_text(palette, encoding="utf-8")
    (directory / "metatiles.bin").write_bytes(struct.pack("<8H", 0x1C00, *([0] * 7)))
    (directory / "metatile_attributes.bin").write_bytes(struct.pack("<H", 0x2002))
    (tmp_path / "src/data/tilesets").mkdir(parents=True)
    (tmp_path / "src/graphics.c").write_text("", encoding="utf-8")
    header = "const struct Tileset gTileset_General = {\n.isCompressed = TRUE, .isSecondary = FALSE,\n"
    header += ".tiles = gTilesetTiles_General, .palettes = gTilesetPalettes_General,\n"
    header += ".metatiles = gMetatiles_General, .metatileAttributes = gMetatileAttributes_General, .callback = NULL,};"
    (tmp_path / "src/data/tilesets/headers.h").write_text(header, encoding="utf-8")
    graphics = 'const u32 gTilesetTiles_General[] = INCGFX_U32("data/tilesets/primary/general/tiles.png", ".4bpp.lz");'
    graphics += (
        'const u16 gTilesetPalettes_General[][16] = {INCGFX_U16("data/tilesets/primary/general/palettes/00.pal")} ;'
    )
    (tmp_path / "src/data/tilesets/graphics.h").write_text(graphics, encoding="utf-8")
    metatiles = 'const u16 gMetatiles_General[] = INCBIN_U16("data/tilesets/primary/general/metatiles.bin");'
    metatiles += (
        'const u16 gMetatileAttributes_General[] = INCBIN_U16("data/tilesets/primary/general/metatile_attributes.bin");'
    )
    (tmp_path / "src/data/tilesets/metatiles.h").write_text(metatiles, encoding="utf-8")
    return tmp_path


def test_hoenn_pixels_palettes_and_attributes(tileset_repo: Path) -> None:
    tileset = read_tilesets(tileset_repo, ruby=False, remake=False)["gTileset_General"]
    assert tileset.pixels == bytes([3] * 64)
    assert tileset.tile_count == 1
    assert tileset.palettes[0][0] == (248, 128, 0)
    assert tileset.metatiles[0].behavior == 2
    assert tileset.metatiles[0].layer_type == 2
    assert tileset.metatiles[0].encounter_type is None
    assert tileset.primary_palette_count == 6
    assert tileset.primary_metatile_count == 512


def test_remake_attributes_are_u32(tileset_repo: Path) -> None:
    path = tileset_repo / "data/tilesets/primary/general/metatile_attributes.bin"
    path.write_bytes(struct.pack("<I", (2 << 29) | (1 << 24) | (7 << 9) | 0x102))
    tileset = read_tilesets(tileset_repo, ruby=False, remake=True)["gTileset_General"]
    tile = tileset.metatiles[0]
    assert (tile.behavior, tile.layer_type, tile.terrain, tile.encounter_type) == (0x102, 2, 7, 1)
    assert tileset.primary_palette_count == 7
    assert tileset.primary_metatile_count == 640


def test_mismatched_attribute_count_fails(tileset_repo: Path) -> None:
    (tileset_repo / "data/tilesets/primary/general/metatile_attributes.bin").write_bytes(b"")
    with pytest.raises(ValueError, match="attributs incohérents"):
        read_tilesets(tileset_repo, ruby=False, remake=False)


def test_non_4bpp_image_fails(tileset_repo: Path) -> None:
    path = tileset_repo / "data/tilesets/primary/general/tiles.png"
    Image.new("RGB", (8, 8)).save(path)
    with pytest.raises(ValueError, match="4 bpp"):
        read_tilesets(tileset_repo, ruby=False, remake=False)


def test_invalid_palette_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.pal"
    path.write_text("JASC-PAL\n0100\n16\n" + "256 0 0\n" * 16, encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.pal"):
        read_palette(path)


@pytest.mark.pipeline
@pytest.mark.parametrize(
    ("game", "count"), list(zip(GEN3_GAMES, (58, 75, 68), strict=True)), ids=[game.version_group for game in GEN3_GAMES]
)
def test_all_pinned_tilesets(game: Game, count: int, source_cache_ready: None) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    repo = Gen3PretRepo(root, game.pret_versions)
    assert len(repo.tilesets) == count
    assert all(len(row.palettes) == 16 for row in repo.tilesets.values())
    assert all(len(tile.tiles) == 8 for row in repo.tilesets.values() for tile in row.metatiles)
    assert all(row.primary_palette_count == (7 if repo.remake else 6) for row in repo.tilesets.values())


def test_ruby_assembler_headers(tileset_repo: Path) -> None:
    directory = tileset_repo / "data/tilesets"
    header = (
        "gTileset_General::\n.byte TRUE\n.byte FALSE\n.2byte 0\n.4byte gTilesetTiles_General\n"
        ".4byte gTilesetPalettes_General\n.4byte gMetatiles_General\n.4byte gMetatileAttributes_General\n"
        ".4byte TilesetCB_General\n.align 2"
    )
    (directory / "headers.inc").write_text(header, encoding="utf-8")
    graphics = (
        'gTilesetTiles_General::\n.incbin "data/tilesets/primary/general/tiles.4bpp.lz"\n'
        'gTilesetPalettes_General::\n.incbin "data/tilesets/primary/general/palettes/00.gbapal"'
    )
    (directory / "graphics.inc").write_text(graphics, encoding="utf-8")
    metatiles = (
        'gMetatiles_General::\n.incbin "data/tilesets/primary/general/metatiles.bin"\n'
        'gMetatileAttributes_General::\n.incbin "data/tilesets/primary/general/metatile_attributes.bin"'
    )
    (directory / "metatiles.inc").write_text(metatiles, encoding="utf-8")
    (tileset_repo / "src/data/graphics.c").write_text("", encoding="utf-8")
    row = read_tilesets(tileset_repo, ruby=True, remake=False)["gTileset_General"]
    assert row.animation_callback == "TilesetCB_General"
    assert row.compressed is True
    assert row.metatiles[0].behavior == 2


@pytest.mark.parametrize("remake", [False, True])
def test_palette_partition_matches_each_engine(tileset_repo: Path, remake: bool) -> None:
    primary = read_tilesets(tileset_repo, ruby=False, remake=False)["gTileset_General"]
    split = 7 if remake else 6
    primary = replace(primary, primary_palette_count=split)
    blue = tuple(((0, 0, 248),) * 16 for _ in range(16))
    secondary = replace(primary, const="gTileset_Test", secondary=True, palettes=blue)
    combined = map_palettes(primary, secondary)
    assert len(combined) == 13
    assert combined[split - 1][0] == (248, 128, 0)
    assert combined[split][0] == (0, 0, 248)
    with pytest.raises(ValueError, match="incompatible"):
        map_palettes(secondary, primary)
