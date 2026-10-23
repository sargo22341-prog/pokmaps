"""Un point visible localement peut être couvert par la carte voisine dans le monde HGSS."""

from pathlib import Path

from PIL import Image

from pokemaps_data.world_placement_hgss import visible_world_cells


def test_neighboring_tree_removes_a_water_point_from_the_final_world(tmp_path: Path) -> None:
    Image.new("RGBA", (128, 128), (20, 150, 220, 255)).save(tmp_path / "local.png")
    folder = tmp_path / "plans/kanto-exterieurs/0"
    folder.mkdir(parents=True)
    image = Image.new("RGBA", (256, 256), (20, 150, 220, 255))
    image.putpixel((24, 24), (82, 115, 41, 255))
    image.save(folder / "0_1.webp", "WEBP", lossless=True)
    rejected = []
    result = visible_world_cells(
        tmp_path,
        dict(image="local.png", const="MAP_ROUTE_12"),
        {"water": [(24, 24), (40, 40)]},
        dict(id="kanto-exterieurs", layout="native", level_count=1),
        [256, 0],
        rejected,
    )
    assert result == {"water": [(40, 40)]}
    assert rejected == [dict(point=(24, 24), kind="water", reason="décor masqué dans le plan extérieur final")]


def test_an_individual_interior_does_not_need_a_world_tile(tmp_path: Path) -> None:
    cells = {"floor": [(24, 24)]}
    assert visible_world_cells(tmp_path, {}, cells, dict(layout="atlas"), [0, 0], []) is cells
