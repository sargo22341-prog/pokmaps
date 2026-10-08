"""Lecture et écriture de tools/data/map_spots.csv."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pokemaps_data.builder_maps import _SpotRows
from pokemaps_data.games import GAMES
from pokemaps_data.map_spots import TerrainKey, read_spots, selected_key, write_spots

if TYPE_CHECKING:
    from pokemaps_data.maps_layout import GameMaps
    from pokemaps_data.pret_gen2 import Gen2PretRepo

HEADER = "family,map_identifier,kind,x,y\n"
ROUTE_1 = TerrainKey("red-blue-yellow", "route-1", "grass")
CERULEAN = TerrainKey("red-blue-yellow", "cerulean-city", "water")


def write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "map_spots.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_missing_file_has_no_curation(tmp_path: Path) -> None:
    assert read_spots(tmp_path / "absent.csv") == {}


def test_round_trip_keeps_points_and_empty_terrains(tmp_path: Path) -> None:
    path = tmp_path / "map_spots.csv"
    spots = {ROUTE_1: frozenset({(808, 3176), (856, 3224)}), CERULEAN: frozenset()}
    write_spots(spots, path)
    assert read_spots(path) == spots
    assert path.read_text(encoding="utf-8").splitlines()[1] == "red-blue-yellow,cerulean-city,water,,"
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("gold-silver,route-1,grass,1,2\n", "famille de cartes inconnue"),
        ("red-blue-yellow,route-1,sand,1,2\n", "terrain inconnu"),
        ("red-blue-yellow,route-1,headbutt,1,2\n", "terrain inconnu"),
        ("red-blue-yellow,,grass,1,2\n", "carte manquante"),
        ("red-blue-yellow,route-1,grass,1,\n", "coordonnées invalides"),
        ("red-blue-yellow,route-1,grass,a,2\n", "coordonnées invalides"),
        ("red-blue-yellow,route-1,grass,1,2\nred-blue-yellow,route-1,grass,1,2\n", "en double"),
        ("red-blue-yellow,route-1,grass,,\nred-blue-yellow,route-1,grass,1,2\n", "à la fois vides et remplis"),
    ],
)
def test_invalid_rows_name_the_problem(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        read_spots(write(tmp_path, body))


def test_old_header_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "map_spots.csv"
    path.write_text("map_identifier,kind,x,y\nroute-1,grass,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="en-tête attendu"):
        read_spots(path)


def test_repository_file_is_valid() -> None:
    assert read_spots()


def test_trees_and_rocks_of_a_game_in_progress(tmp_path: Path) -> None:
    body = "gold-silver-crystal,route-29,tree,104,40\ngold-silver-crystal,cianwood-city,rock,,\n"
    spots = read_spots(write(tmp_path, body))
    assert spots[TerrainKey("gold-silver-crystal", "route-29", "tree")] == {(104, 40)}
    assert spots[TerrainKey("gold-silver-crystal", "cianwood-city", "rock")] == frozenset()
    # L'application ne construit pas Or et Argent : leurs emplacements retouchés n'y sont pas vérifiés.
    rows = _SpotRows(spots, GAMES)
    rows.check_all_used({"red-blue-yellow"})
    with pytest.raises(ValueError, match="cartes absentes des jeux de leur famille"):
        rows.check_all_used({"red-blue-yellow", "gold-silver-crystal"})


def test_gen2_curated_points_stay_on_their_target_terrain(
    gold_silver_maps: "GameMaps", crystal_repo: "Gen2PretRepo"
) -> None:
    from pokemaps_data.games import CRYSTAL
    from pokemaps_data.maps_layout import GameMaps, read_layout_curation

    crystal_maps = GameMaps(crystal_repo, CRYSTAL, read_layout_curation())
    curated = {key: points for key, points in read_spots().items() if key.family == "gold-silver-crystal"}
    assert len(curated) >= 26
    for key, points in curated.items():
        const = key.map_identifier.upper().replace("-", "_")
        for maps in (gold_silver_maps, crystal_maps):
            group = maps.game.version_group
            if key.version_group and key.version_group != group:
                continue
            if selected_key(curated, key, group) != key:
                continue
            valid = {maps.point(const, x, y) for x, y in maps.cells(const)[key.kind]}
            assert points <= valid, key
