"""Herbe HGSS : les chemins, l'eau et les arbres ne reçoivent plus les points de marche."""

from pathlib import Path

from PIL import Image

from pokemaps_data.grass_placement_hgss import align_grass


def test_visible_grass_replaces_points_on_a_path_and_a_tree(tmp_path: Path) -> None:
    image = Image.new("RGB", (80, 64), (115, 222, 165))
    image.paste((66, 165, 99), (32, 0, 80, 64))
    image.putpixel((40, 24), (140, 198, 49))
    path = tmp_path / "route.png"
    image.save(path)
    terrain = {"grass": [(8, 24), (40, 24), (56, 24)], "water": [(8, 56)]}
    result = align_grass(path, terrain, "MAP_ROUTE_30")
    assert (8, 24) not in result["grass"]
    assert (40, 24) not in result["grass"]
    assert (56, 24) in result["grass"]
    assert result["water"] == terrain["water"]
    assert terrain["grass"] == [(8, 24), (40, 24), (56, 24)]


def test_cave_uses_validated_floor_instead_of_spurious_grass(tmp_path: Path) -> None:
    path = tmp_path / "cave.png"
    Image.new("RGB", (64, 64), (74, 82, 82)).save(path)
    terrain = {"grass": [(8, 8)], "floor": [(24, 24)]}
    assert align_grass(path, terrain, "MAP_UNION_CAVE_1F") == {"floor": [(24, 24)]}
    assert align_grass(path, terrain, "MAP_SAFARI_ZONE_06") == terrain


def test_special_mountainside_keeps_its_native_nonstandard_grass(tmp_path: Path) -> None:
    path = tmp_path / "mountain.png"
    Image.new("RGB", (64, 64), (115, 156, 115)).save(path)
    terrain = {"grass": [(24, 24)]}
    assert align_grass(path, terrain, "MAP_MOUNT_SILVER_CAVE_UPPER_MOUNTAINSIDE") == terrain
