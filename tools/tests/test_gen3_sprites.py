"""Premières images des objets GBA : taille DMA et dimensions graphiques distinctes."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import FIRERED_LEAFGREEN, GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_sprites import _tables, sprite_image
from pokemaps_data.sources import pret_dir


@pytest.fixture
def sprite_repo(tmp_path: Path) -> Gen3PretRepo:
    directory = tmp_path / "src/data/object_events"
    directory.mkdir(parents=True)
    (tmp_path / "graphics").mkdir()
    (directory / "object_event_graphics_info_pointers.h").write_text("[OBJ_EVENT_GFX_SHIP] = &gShip,", encoding="utf-8")
    (directory / "object_event_graphics_info.h").write_text(
        "const struct ObjectEventGraphicsInfo gShip = {"
        ".width = 16, .height = 16, .images = gFrames, .paletteTag = 0x1100 };",
        encoding="utf-8",
    )
    (directory / "object_event_graphics.h").write_text(
        'const u16 gPic[] = INCBIN_U16("graphics/ship.4bpp");\n'
        'const u16 gObjectEventPal_Ship[] = INCBIN_U16("graphics/ship.gbapal");',
        encoding="utf-8",
    )
    (directory / "object_event_pic_tables.h").write_text(
        "const struct SpriteFrameImage gFrames[] = { overworld_frame(gPic, 1, 4, 1), };",
        encoding="utf-8",
    )
    (tmp_path / "src/event_object_movement.c").write_text(
        "#define OBJ_EVENT_PAL_TAG_SHIP 0x1100\n{ gObjectEventPal_Ship, OBJ_EVENT_PAL_TAG_SHIP }",
        encoding="utf-8",
    )
    (tmp_path / "graphics/ship.pal").write_text(
        "JASC-PAL\n0100\n16\n" + "\n".join(f"{shade} 0 0" for shade in range(16)), encoding="utf-8"
    )
    image = Image.new("P", (16, 32), 1)
    image.putpalette([value for shade in range(256) for value in (shade, 0, 0)])
    image.paste(2, (0, 16, 16, 32))
    image.putpixel((0, 16), 0)
    image.save(tmp_path / "graphics/ship.png")
    return Gen3PretRepo(tmp_path, FIRERED_LEAFGREEN.pret_versions)


def test_dma_factors_can_differ_from_sprite_dimensions(sprite_repo: Gen3PretRepo) -> None:
    image = sprite_image(sprite_repo, "OBJ_EVENT_GFX_SHIP")
    assert image.size == (16, 16)
    assert image.getpixel((0, 0)) == (0, 0, 0, 0)
    assert image.getpixel((15, 15)) == (2, 0, 0, 255)


def test_sprite_dma_size_must_still_match(sprite_repo: Gen3PretRepo) -> None:
    path = sprite_repo.root / "src/data/object_events/object_event_pic_tables.h"
    path.write_text(path.read_text("utf-8").replace("1, 4, 1", "1, 3, 1"), encoding="utf-8")
    with pytest.raises(ValueError, match="taille de la première image incohérente"):
        sprite_image(sprite_repo, "OBJ_EVENT_GFX_SHIP")


@pytest.mark.pipeline
@pytest.mark.parametrize("game", GEN3_GAMES)
def test_all_distributed_gba_sprites_keep_pinned_engine_dimensions(game: Game) -> None:
    tools = Path(__file__).resolve().parents[1]
    repo = Gen3PretRepo(pret_dir(tools / ".cache", game.pret_repo), game.pret_versions)
    pointers, info, _, _ = _tables(repo)
    directory = tools.parent / "app/src/main/assets/maps" / game.version_group / "sprites"
    sprites = tuple(directory.glob("*.webp"))
    assert sprites
    for path in sprites:
        symbol = path.stem.upper().replace("-", "_")
        fields = info[pointers[symbol]]
        with Image.open(path) as image:
            assert image.size == (int(fields["width"]), int(fields["height"])), path.name
