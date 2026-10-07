"""Lecture et écriture de tools/data/map_spots.csv."""

from pathlib import Path

import pytest

from pokemaps_data.map_spots import TerrainKey, read_spots, write_spots

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
    assert all(key.family == "red-blue-yellow" for key in read_spots())
