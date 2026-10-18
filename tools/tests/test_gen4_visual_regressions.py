"""Régressions des répétitions de textures, des poses de face et de l'espacement des duos DS."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pokemaps_data import maps_sprites_gen4
from pokemaps_data.maps_actor_positions_gen4 import space_trainer_duos
from pokemaps_data.maps_characters import ObjectRow
from pokemaps_data.maps_render_gen4 import _material
from pokemaps_data.maps_sprites_gen4 import _png_frame
from pokemaps_data.pret_gen4_nitro import read_nsbmd
from pokemaps_data.pret_gen4_textures import PALETTE_16, NitroTextures, Palette, Texture

from .test_gen4_nitro import nsbmd


@pytest.mark.parametrize("parameters", [0, 0x30000, 0x70000, 0xF0000])
def test_shared_texture_uses_each_material_repeat_and_mirror(parameters: int) -> None:
    [model] = read_nsbmd(nsbmd(bytes([1])), "sol").models
    material = replace(model.materials[0], texture="herbe", palette="herbe_pl", texture_parameters=parameters)
    source = Texture("herbe", 8, 8, PALETTE_16, False, (False, False), (False, False), bytes(range(32)))
    textures = NitroTextures({"herbe": source}, {"herbe_pl": Palette("herbe_pl", tuple(range(16)))})
    raster = _material(material, None, (textures,))
    assert raster.texture is not None
    expected = replace(
        source,
        repeat=(bool(parameters & 0x10000), bool(parameters & 0x20000)),
        flip=(bool(parameters & 0x40000), bool(parameters & 0x80000)),
    )
    assert raster.texture.source == expected
    assert textures.textures["herbe"] == source
    x = (6 if parameters & 0x40000 else 1) if parameters & 0x10000 else 7
    y = (6 if parameters & 0x80000 else 1) if parameters & 0x20000 else 7
    assert raster.texture.sample(9, 9) == raster.texture.sample(x, y)


@pytest.mark.parametrize(
    "frames,category,expected", [(16, "32_px_single_palette", 4), (1, "single_frame", 0), (2, "two_frame_pokemon", 0)]
)
def test_png_selects_front_without_changing_static_objects(
    tmp_path: Path, frames: int, category: str, expected: int
) -> None:
    folder = tmp_path / "res/graphics/field_sprites"
    folder.mkdir(parents=True)
    (folder / "meson.build").write_text(f"field_sprites_textures_{category} = ['actor.png']", encoding="utf-8")
    image = Image.new("RGBA", (32, 32 * frames))
    for frame in range(frames):
        image.paste((frame, 0, 0, 255), (0, frame * 32, 32, (frame + 1) * 32))
    path = folder / "actor.png"
    image.save(path)
    result = _png_frame(SimpleNamespace(root=tmp_path), path)
    assert result.size == (32, 32)
    assert result.getpixel((16, 16)) == (expected, 0, 0, 255)


def _twin(x: int, name: str = "Jumelles") -> ObjectRow:
    return ObjectRow("ROUTE", "trainer", x, 40, "2", None, None, None, "twins", name_fr=name)


def test_nitro_front_frame_is_selected_in_numeric_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "actor.nsbtx"
    path.write_bytes(b"source")
    textures = {
        f"actor.{index}": Texture(
            f"actor.{index}", 8, 8, PALETTE_16, False, (False, False), (False, False), bytes([index - 1] * 32)
        )
        for index in sorted(range(1, 17), key=str)
    }
    catalog = NitroTextures(textures, {"actor": Palette("actor", tuple(range(16)))})
    monkeypatch.setattr(maps_sprites_gen4, "read_nsbtx", lambda *_: catalog)
    front = maps_sprites_gen4._nitro_frame(path)
    assert front.getpixel((0, 0)) == (33, 0, 0, 255)


def test_duo_keeps_its_center_and_source_cells_with_more_space() -> None:
    left, right = _twin(40), _twin(56)
    left.source_cell, right.source_cell = (2, 3), (3, 3)
    unrelated = _twin(72, "Autre duo")
    space_trainer_duos([right, unrelated, left])
    assert (left.x, right.x, unrelated.x) == (36, 60, 72)
    assert (left.source_cell, right.source_cell) == ((2, 3), (3, 3))
    space_trainer_duos([left, right])
    assert (left.x, right.x) == (36, 60)


def test_vertical_duo_leaves_room_for_the_sprite_height() -> None:
    top, bottom = _twin(40), _twin(40)
    bottom.y = 56
    space_trainer_duos([bottom, top])
    assert (top.x, top.y, bottom.x, bottom.y) == (40, 32, 40, 64)
