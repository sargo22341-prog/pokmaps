"""Curations GBA sans sources : rognage d'un layout, regroupement des lits et tuiles d'une région de carte."""

from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.maps_curation_gen3 import MapTrim, trim_maps
from pokemaps_data.maps_facilities_gen3 import _adjacent_groups
from pokemaps_data.maps_render import level_count, write_region_tiles
from pokemaps_data.pret_gen3_maps import Gen3Event, Gen3Layout, Gen3Map, Gen3Warp

FAMILY = "firered-leafgreen"


def _map(cells: tuple[int, ...], width: int, warps: tuple[Gen3Warp, ...] = ()) -> Gen3Map:
    layout = Gen3Layout("LAYOUT_TEST", width, len(cells) // width, "gTileset_A", "gTileset_B", cells, 2, 2, (1,) * 4)
    return Gen3Map(
        "MAP_TEST", "Test", 1, 0, 0, layout, "MAP_TYPE_UNDERGROUND", "", (), warps, (), (), (), None, None, ()
    )


def test_trim_removes_a_uniform_band_without_events() -> None:
    maps = {"MAP_TEST": _map((1, 2, 9, 3, 4, 9), 3, (Gen3Warp(1, 1, "MAP_OTHER", 1, 0),))}
    trim_maps(maps, [MapTrim(FAMILY, "MAP_TEST", 2, 2)])
    layout = maps["MAP_TEST"].layout
    assert (layout.width, layout.height, layout.cells) == (2, 2, (1, 2, 3, 4))
    assert layout.const == "LAYOUT_TEST_TRIMMED"


@pytest.mark.parametrize(
    ("current", "trim", "message"),
    [
        (_map((1, 2, 9, 3, 4, 8), 3), MapTrim(FAMILY, "MAP_TEST", 2, 2), "bande retirée non uniforme"),
        (
            _map((1, 2, 9, 3, 4, 9), 3, (Gen3Warp(2, 0, "MAP_OTHER", 1, 0),)),
            MapTrim(FAMILY, "MAP_TEST", 2, 2),
            "événement dans la bande retirée",
        ),
        (_map((1, 2, 9, 3, 4, 9), 3), MapTrim(FAMILY, "MAP_TEST", 3, 2), "ne réduisent pas"),
        (_map((1, 2, 9, 3, 4, 9), 3), MapTrim(FAMILY, "MAP_ABSENT", 2, 2), "carte inconnue"),
    ],
)
def test_trim_rejects_a_band_that_belongs_to_the_map(current: Gen3Map, trim: MapTrim, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        trim_maps({"MAP_TEST": current}, [trim])


def test_trim_rejects_a_sign_in_the_removed_band() -> None:
    current = replace(_map((1, 2, 3, 4, 9, 9), 2), bg_events=(Gen3Event("sign", 0, 2, 0, ()),))
    with pytest.raises(ValueError, match="événement dans la bande retirée"):
        trim_maps({"MAP_TEST": current}, [MapTrim(FAMILY, "MAP_TEST", 2, 2)])


def test_bed_cells_are_grouped_by_furniture() -> None:
    # Le lit à quatre cases du Centre Météo, le lit à deux cases du M.S. Marée et un lit isolé.
    cells = [(4, 4), (5, 4), (4, 5), (5, 5), (10, 2), (10, 3), (1, 1)]
    assert _adjacent_groups(cells) == [[(1, 1)], [(4, 4), (4, 5), (5, 4), (5, 5)], [(10, 2), (10, 3)]]
    assert _adjacent_groups([(0, 0), (2, 0)]) == [[(0, 0)], [(2, 0)]]


def test_region_tiles_only_cover_the_touched_area_at_every_level(tmp_path: Path) -> None:
    size = (2048, 1024)
    image = Image.new("RGBA", (48, 32), (200, 40, 40, 255))
    count = write_region_tiles(image, (528, 272), size, tmp_path)
    levels = level_count(*size)
    written = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*.webp"))
    assert count == len(written) == levels
    assert written == ["0/0_0.webp", "1/0_0.webp", "2/0_1.webp", "3/1_2.webp"]
    with Image.open(tmp_path / "3/1_2.webp") as tile:
        assert tile.size == (256, 256)
        assert tile.getpixel((528 - 512, 272 - 256)) == (200, 40, 40, 255)
        assert tile.getpixel((528 - 512 - 1, 272 - 256))[3] == 0
        assert tile.getpixel((528 - 512 + 48, 272 - 256))[3] == 0
    with Image.open(tmp_path / "0/0_0.webp") as tile:
        # Au niveau le plus réduit (facteur 8), la zone tient dans quelques pixels opaques, alignés sur la carte.
        assert tile.getpixel((66, 34)) == (200, 40, 40, 255)
