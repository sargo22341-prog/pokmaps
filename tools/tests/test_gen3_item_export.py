"""Les métadonnées de l'aperçu suivent chaque objet réellement inséré dans Room."""

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.pret_gen3_items import Gen3MapItem
from pokemaps_data.preview_items_gen3 import validate_item_metadata, write_item_metadata


@pytest.fixture
def item_database(tmp_path: Path) -> Path:
    path = tmp_path / "pokedex.db"
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            "CREATE TABLE map (id INTEGER, identifier TEXT);"
            "CREATE TABLE version (id INTEGER, identifier TEXT);"
            "CREATE TABLE map_object (map_id INTEGER, version_id INTEGER, kind TEXT, x INTEGER, y INTEGER);"
            "INSERT INTO map VALUES (1, 'test');"
            "INSERT INTO version VALUES (1, 'ruby');"
            "INSERT INTO map_object VALUES (1, 1, 'item', 40, 56);"
        )
        connection.commit()
    finally:
        connection.close()
    return path


def _item() -> Gen3MapItem:
    return Gen3MapItem("MAP_TEST", "ruby", "item", 40, 56, 3, "ITEM_POTION", 2, "FLAG_ITEM", "Gift")


def test_written_metadata_preserves_engine_fields(item_database: Path, tmp_path: Path) -> None:
    output = tmp_path / "map_items.json"
    write_item_metadata(item_database, output, [_item()])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data[0]["quantity"] == 2
    assert data[0]["removal_flag"] == "FLAG_ITEM"
    assert data[0]["elevation"] == 3
    assert data[0]["script"] == "Gift"


@pytest.mark.parametrize("change", [{"x": 41}, {"version": "sapphire"}, {"kind": "hidden_item"}])
def test_wrong_position_version_or_kind_stops_export(item_database: Path, change: dict[str, str | int]) -> None:
    with pytest.raises(ValueError, match="incohérentes"):
        validate_item_metadata(item_database, [replace(_item(), **change)])


def test_missing_metadata_stops_export(item_database: Path) -> None:
    with pytest.raises(ValueError, match="absents du JSON"):
        validate_item_metadata(item_database, [])


def test_duplicate_metadata_stops_export(item_database: Path) -> None:
    with pytest.raises(ValueError, match="absents de la base"):
        validate_item_metadata(item_database, [_item(), _item()])


def test_coins_are_conserved_without_a_fake_room_item(item_database: Path, tmp_path: Path) -> None:
    output = tmp_path / "map_items.json"
    coins = replace(_item(), kind="hidden_coins", item="ITEM_NONE", quantity=100)
    write_item_metadata(item_database, output, [_item(), coins])
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data[1]["kind"] == "hidden_coins"
    assert data[1]["quantity"] == 100
