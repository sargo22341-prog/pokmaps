"""Bornes des assemblages et séparation des niveaux DS sans sources téléchargées."""

from dataclasses import replace

import pytest

from pokemaps_data.maps import read_map_names
from pokemaps_data.maps_bindings_gen4 import PaletteBinding, bind_palettes
from pokemaps_data.maps_layout_gen4 import _matrix_blocks
from pokemaps_data.maps_levels_gen4 import lower_surfaces
from pokemaps_data.maps_tiles_gen4 import overlaps, render_batch
from pokemaps_data.pret_gen4_land import COLLISION_BIT, LandBlock, PlatinumBdhc
from pokemaps_data.pret_gen4_map_models import Gen4Matrix
from pokemaps_data.pret_gen4_textures import NitroTextures, Palette

ONE = 4096


@pytest.mark.parametrize("family", ["platinum", "diamond-pearl"])
def test_french_locations_keep_ds_names_instead_of_remake_names(family: str) -> None:
    names = read_map_names()[family]
    for token, expected in (
        ("WAYWARD_CAVE", "Grotte Revêche"),
        ("TURNBACK_CAVE", "Grotte Retour"),
        ("SOLACEON_RUINS", "Ruines Bonville"),
        ("LOST_TOWER", "Tour Perdue"),
    ):
        selected = [name for const, name in names.items() if token in const and "DISTORTION_WORLD" not in const]
        assert selected and all(name.startswith(expected) for name in selected)


def test_matrix_owners_are_selected_without_overlapping_blocks() -> None:
    matrix = Gen4Matrix(0, "monde", ((1, 2, 3), (4, 5, 6)), ((10, 0, 20), (0, 0, 0)), None)
    blocks = _matrix_blocks(matrix, [10, 20], {10: None, 20: None})
    assert [(block.column, block.row, block.header) for block in blocks] == [(0, 0, 10), (1, 0, 10), (2, 0, 20)]
    assert len({(block.column, block.row) for block in blocks}) == len(blocks)


def test_missing_matrix_owner_is_an_error() -> None:
    matrix = Gen4Matrix(0, "vide", ((1,),), ((0,),), None)
    with pytest.raises(ValueError, match="aucun bloc utilisé"):
        _matrix_blocks(matrix, [10], {10: None})


def test_excluded_named_cell_is_not_rendered_as_filler() -> None:
    matrix = Gen4Matrix(0, "monde", ((1, 128, 3),), ((10, 472, 20),), None)
    blocks = _matrix_blocks(matrix, [10, 20], {10: None, 20: None})
    assert [(block.column, block.block) for block in blocks] == [(0, 1), (2, 3)]


def _two_surfaces(upper_end: int = 256) -> LandBlock:
    bdhc = PlatinumBdhc(
        ((-256 * ONE, -256 * ONE), (256 * ONE, 256 * ONE), (upper_end * ONE, upper_end * ONE)),
        ((0, ONE, 0),),
        (0, -32 * ONE),
        ((0, 1, 0, 0), (0, 2, 0, 1)),
        (),
        (),
    )
    return LandBlock((0,) * 1024, (), b"", bdhc)


def test_bridge_has_a_lower_plan_at_the_correct_altitude() -> None:
    (lower,) = lower_surfaces(_two_surfaces(), 2)
    assert lower is not None
    assert lower.ceiling == 48 * ONE - 1
    assert len(lower.cells) == 1024


def test_colliding_furniture_and_isolated_surface_do_not_create_a_plan() -> None:
    assert lower_surfaces(replace(_two_surfaces(), attributes=(COLLISION_BIT,) * 1024), 0) == ()
    assert lower_surfaces(_two_surfaces(-240), 0) == ()


def test_four_superposed_floors_keep_all_three_lower_levels() -> None:
    source = _two_surfaces()
    bdhc = replace(
        source.bdhc,
        constants=(0, -160 * ONE, -320 * ONE, -480 * ONE),
        plates=tuple((0, 1, 0, height) for height in range(4)),
    )
    surfaces = lower_surfaces(replace(source, bdhc=bdhc), 0)
    assert [surface.ceiling for surface in surfaces] == [160 * ONE - 1, 320 * ONE - 1, 480 * ONE - 1]
    assert all(len(surface.cells) == 1024 for surface in surfaces)


def test_palette_corrections_are_scoped_and_never_hide_a_missing_target() -> None:
    textures = NitroTextures({}, {"sol": Palette("sol", (0, 31))})
    binding = PaletteBinding("platinum", 71, "ancien", "sol")
    assert bind_palettes(textures, "diamond-pearl", 71, (binding,)).palettes == textures.palettes
    result = bind_palettes(textures, "platinum", 71, (binding,))
    assert result.palettes["ancien"] == textures.palettes["sol"]
    assert "ancien" not in textures.palettes
    with pytest.raises(ValueError, match="devenue invalide"):
        bind_palettes(textures, "platinum", 71, (replace(binding, target="absent"),))


def test_touching_boxes_do_not_overlap_and_empty_render_batch_is_refused() -> None:
    assert not overlaps((0, 0, 512, 512), (512, 0, 1024, 512))
    assert overlaps((0, 0, 512, 512), (511, 0, 1024, 512))
    with pytest.raises(ValueError, match="Lot de rendu"):
        render_batch(())
