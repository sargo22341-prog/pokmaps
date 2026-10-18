"""Remakes activés : base distribuée, variantes et validation du catalogue."""

import json
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.games import FIRERED_LEAFGREEN, GAMES
from pokemaps_data.validate import CHECKS
from pokemaps_data.validate_gen3_characters import validate_character_catalog


def test_remake_versions_and_pokedexes_are_shipped(db: sqlite3.Connection) -> None:
    assert FIRERED_LEAFGREEN in GAMES
    assert dict(db.execute("SELECT id, name_fr FROM version WHERE version_group_id = 7")) == {
        10: "Rouge Feu",
        11: "Vert Feuille",
    }
    assert db.execute("SELECT remake_generation_id FROM version_group WHERE id = 7").fetchone() == (1,)
    rows = db.execute(
        """SELECT p.identifier, count(*) FROM version_group_pokedex vgp
           JOIN pokedex p ON p.id = vgp.pokedex_id JOIN pokedex_entry pe ON pe.pokedex_id = p.id
           JOIN pokemon mon ON mon.id = pe.pokemon_id
           JOIN version_group vg ON vg.id = vgp.version_group_id
           WHERE vgp.version_group_id = 7 AND mon.generation_id <= vg.generation_id GROUP BY p.identifier"""
    ).fetchall()
    assert dict(rows) == {"kanto": 151, "national": 386}


def test_remake_worlds_fixed_pokemon_and_services_are_shipped(db: sqlite3.Connection) -> None:
    worlds = db.execute("SELECT identifier FROM map WHERE version_group_id = 7 AND is_world = 1").fetchall()
    assert {row[0] for row in worlds} == {"kanto", "sevii"}
    for version in (10, 11):
        rows = db.execute(
            """SELECT o.pokemon_id, o.level FROM map_object o JOIN map m ON m.id = o.map_id
               WHERE m.version_group_id = 7 AND o.version_id = ? AND o.kind = 'pokemon'""",
            (version,),
        ).fetchall()
        assert len(rows) == 12
        assert rows.count((143, 30)) == 2 and (97, 30) in rows
        assert (150, 70) in rows and (386, 30) in rows
        kinds = db.execute(
            """SELECT n.kind FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id
               JOIN map m ON m.id = o.map_id WHERE m.version_group_id = 7 AND o.version_id = ?""",
            (version,),
        ).fetchall()
        assert {"fossil", "daycare", "daycare_egg", "move_tutor", "move_deleter", "coin_sale"} <= {
            row[0] for row in kinds
        }


def test_remake_character_catalog_and_version_boundary(assets: Path, tmp_path: Path) -> None:
    folder = assets / "maps/firered-leafgreen"
    validate_character_catalog(folder, FIRERED_LEAFGREEN)
    data = json.loads((folder / "characters.json").read_text("utf-8"))
    data["characters"][0]["version"] = "emerald"
    (tmp_path / "characters.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="version invalide"):
        validate_character_catalog(tmp_path, FIRERED_LEAFGREEN)


def test_remake_casino_uses_version_prices_and_coins(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """SELECT o.version_id, n.price, n.currency FROM npc_offer n
           JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = 7 AND n.kind = 'prize_pokemon' AND n.pokemon_id = 63"""
    ).fetchall()
    assert sorted(rows) == [(10, 180, "coins"), (11, 120, "coins")]
    query = next(query for name, query in CHECKS if name == "offre de personnage incohérente")
    assert db.execute(query).fetchall() == []
    db.execute("UPDATE npc_offer SET currency = 'money' WHERE kind = 'prize_pokemon' AND currency = 'coins'")
    assert db.execute(query).fetchall()


def test_invisible_journals_remain_in_catalog_without_map_actors(assets: Path, db: sqlite3.Connection) -> None:
    data = json.loads((assets / "maps/firered-leafgreen/characters.json").read_text("utf-8"))
    journals = [
        row
        for row in data["characters"]
        if dict(row["event"]["fields"]).get("movement_type") == "MOVEMENT_TYPE_INVISIBLE"
    ]
    assert journals
    for row in journals:
        identifier = row["map_const"].removeprefix("MAP_").lower().replace("_", "-")
        version = 10 if row["version"] == "firered" else 11
        count = db.execute(
            """SELECT count(*) FROM map_object o JOIN map m ON m.id = o.map_id
               WHERE m.version_group_id = 7 AND m.identifier = ? AND o.version_id = ?
               AND o.x = m.x + ? * 16 + 8 AND o.y = m.y + ? * 16 + 8""",
            (identifier, version, row["event"]["x"], row["event"]["y"]),
        ).fetchone()[0]
        assert count == 0, row["key"]
