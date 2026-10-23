"""Surfaces d'eau éditoriales HGSS : décor visible, berges et données invalides."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.water_placement_hgss import read_water_regions, water_points


def test_water_points_keep_the_whole_marker_away_from_shore_and_transparency(tmp_path: Path) -> None:
    image = Image.new("RGBA", (64, 64), (20, 150, 220, 255))
    image.putpixel((16, 16), (0, 180, 0, 255))
    image.putpixel((48, 48), (20, 150, 220, 0))
    path = tmp_path / "pond.png"
    image.save(path)
    points = water_points(path, [(16, 16, 49, 49)])
    assert len(points) == 7
    assert (16, 16) not in points and (48, 48) not in points
    assert (32, 32) in points


def test_only_the_reviewed_pond_is_used_even_with_blue_roofs_elsewhere(tmp_path: Path) -> None:
    path = tmp_path / "town.png"
    Image.new("RGBA", (128, 64), (20, 150, 220, 255)).save(path)
    assert water_points(path, [(16, 16, 49, 49)]) == [(x, y) for x in (16, 32, 48) for y in (16, 32, 48)]


def test_missing_visible_water_and_outside_regions_are_errors(tmp_path: Path) -> None:
    path = tmp_path / "trees.png"
    Image.new("RGBA", (64, 64), (20, 150, 40, 255)).save(path)
    with pytest.raises(ValueError, match="aucune eau visible"):
        water_points(path, [(16, 16, 49, 49)])
    with pytest.raises(ValueError, match="hors image"):
        water_points(path, [(16, 16, 128, 128)])


@pytest.mark.parametrize("bounds", ["1,16,16,8,32,Relecture", "1,16,16,32,32,"])
def test_regions_need_valid_bounds_and_a_reason(tmp_path: Path, bounds: str) -> None:
    path = tmp_path / "regions.csv"
    path.write_text("header,left,top,right,bottom,reason\n" + bounds + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="aquatique"):
        read_water_regions(path)


def test_repeated_regions_are_errors(tmp_path: Path) -> None:
    path = tmp_path / "regions.csv"
    row = "1,16,16,32,32,Relecture\n"
    path.write_text("header,left,top,right,bottom,reason\n" + row * 2, encoding="utf-8")
    with pytest.raises(ValueError, match="répété"):
        read_water_regions(path)
