"""Jeux Hoenn activés : données versionnées, services et différences entre versions."""

import json
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.games import EMERALD, FIRERED_LEAFGREEN, GAMES, RUBY_SAPPHIRE, Game
from pokemaps_data.validate import CHECKS
from pokemaps_data.validate_hoenn_characters import validate_character_catalog


def test_hoenn_versions_and_both_pokedexes_are_shipped(db: sqlite3.Connection) -> None:
    assert RUBY_SAPPHIRE in GAMES and EMERALD in GAMES and FIRERED_LEAFGREEN not in GAMES
    assert dict(db.execute("SELECT id, name_fr FROM version WHERE id >= 7")) == {7: "Rubis", 8: "Saphir", 9: "Émeraude"}
    for group in (5, 6):
        rows = db.execute(
            """SELECT p.identifier, count(*) FROM version_group_pokedex vgp
               JOIN pokedex p ON p.id = vgp.pokedex_id JOIN pokedex_entry pe ON pe.pokedex_id = p.id
               WHERE vgp.version_group_id = ? GROUP BY p.identifier""",
            (group,),
        ).fetchall()
        assert dict(rows) == {"hoenn": 202, "national": 386}


def test_hoenn_map_and_fixed_pokemon_differences(db: sqlite3.Connection) -> None:
    counts = dict(db.execute("SELECT version_group_id, count(*) FROM map WHERE version_group_id >= 5 GROUP BY 1"))
    assert counts[6] > counts[5] > 390
    assert db.execute("SELECT count(*) FROM map_spot WHERE kind = 'underwater'").fetchone()[0] > 0
    rows = db.execute(
        """SELECT o.version_id, o.pokemon_id, o.level FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE o.kind = 'pokemon' AND o.pokemon_id IN (382, 383) AND m.version_group_id >= 5"""
    ).fetchall()
    assert (7, 383, 45) in rows and (8, 382, 45) in rows
    assert (9, 383, 70) in rows and (9, 382, 70) in rows


def test_hoenn_services_and_currency_are_preserved(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """SELECT n.kind, n.price, n.currency FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id
           JOIN map m ON m.id = o.map_id WHERE m.version_group_id >= 5"""
    ).fetchall()
    kinds = {kind for kind, _, _ in rows}
    assert {"fossil", "daycare", "daycare_egg", "daycare_withdrawal", "move_relearner", "fruit_tree"} <= kinds
    assert ("sale", 48, "battle_points") in rows
    assert ("sale", 250, "ashes") in rows
    assert ("move_tutor", None, None) in rows
    assert {("sale", price, "money") for price in (200, 300, 350)} <= set(rows)
    assert (
        db.execute(
            """SELECT count(*) FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id
           JOIN map m ON m.id = o.map_id WHERE n.kind = 'move_relearner' AND n.wanted_item_id IS NOT NULL
           AND m.version_group_id >= 5"""
        ).fetchone()[0]
        > 0
    )


@pytest.mark.parametrize("assignment", ["currency = 'unknown'", "wanted_item_id = NULL"])
def test_invalid_hoenn_offer_is_rejected(db: sqlite3.Connection, assignment: str) -> None:
    db.execute(f"UPDATE npc_offer SET {assignment} WHERE kind = 'move_relearner'")
    query = next(query for name, query in CHECKS if name == "offre de personnage incohérente")
    assert db.execute(query).fetchall()


@pytest.mark.parametrize("game", (RUBY_SAPPHIRE, EMERALD), ids=lambda game: game.version_group)
def test_hoenn_character_catalog_is_valid(assets: Path, game: Game) -> None:
    validate_character_catalog(assets / "maps" / game.version_group, game)


def test_character_catalog_rejects_wrong_source(assets: Path, tmp_path: Path) -> None:
    data = json.loads((assets / "maps/emerald/characters.json").read_text("utf-8"))
    data["commit"] = "wrong"
    (tmp_path / "characters.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="source"):
        validate_character_catalog(tmp_path, EMERALD)


def test_shared_events_keep_their_distinct_maps_and_reject_real_duplicates(assets: Path, tmp_path: Path) -> None:
    data = json.loads((assets / "maps/ruby-sapphire/characters.json").read_text("utf-8"))
    events = [row for row in data["characters"] if row["version"] == "ruby" and row["key"] == "Route130:1"]
    assert {row["map_const"] for row in events} == {"MAP_ROUTE130", "MAP_ROUTE130_MIRAGE_ISLAND"}
    data["characters"].append(data["characters"][0])
    (tmp_path / "characters.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="répété"):
        validate_character_catalog(tmp_path, RUBY_SAPPHIRE)
