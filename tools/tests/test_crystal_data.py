"""Cristal : données livrées, rencontres et offres propres à la version."""

import sqlite3

import pytest

from pokemaps_data.games import CRYSTAL, GAMES
from pokemaps_data.validate import CHECKS


def _offers(db: sqlite3.Connection, identifier: str, kind: str) -> list[tuple]:
    return db.execute(
        """SELECT p.identifier, i.identifier, n.quantity, n.price, w.identifier FROM npc_offer n
           JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           LEFT JOIN pokemon p ON p.id = n.pokemon_id LEFT JOIN item i ON i.id = n.item_id
           LEFT JOIN pokemon w ON w.id = n.wanted_pokemon_id
           WHERE m.version_group_id = 4 AND m.identifier = ? AND n.kind = ?""",
        (identifier, kind),
    ).fetchall()


def test_crystal_is_shipped_with_suicune_cover(db: sqlite3.Connection) -> None:
    assert CRYSTAL in GAMES
    assert db.execute("SELECT name_fr, mascot_pokemon_id FROM version WHERE id = 6").fetchone() == ("Cristal", 245)
    assert db.execute("SELECT count(*) FROM pokedex_entry WHERE pokedex_id = 3").fetchone()[0] == 251
    assert db.execute("SELECT count(*) FROM map WHERE version_group_id = 4 AND is_world = 1").fetchone()[0] == 2


def test_crystal_tutor_and_buena_currency(db: sqlite3.Connection) -> None:
    assert _offers(db, "goldenrod-city", "move_tutor") == [(None, None, None, 4000, None)]
    prizes = _offers(db, "radio-tower-2f", "point_prize")
    assert len(prizes) == 9
    assert (None, "ultra-ball", None, 2, None) in prizes
    assert (None, "rare-candy", None, 3, None) in prizes
    assert (
        db.execute("SELECT count(*) FROM pokemon_move WHERE version_group_id = 4 AND method = 'tutor'").fetchone()[0]
        == 220
    )


def test_crystal_eggs_dratini_and_trades(db: sqlite3.Connection) -> None:
    eggs = _offers(db, "day-care", "gift_egg")
    assert {row[0] for row in eggs} == {"pichu", "cleffa", "igglybuff", "tyrogue", "smoochum", "elekid", "magby"}
    assert all(row[2] == 5 for row in eggs)
    assert ("dratini", None, 15, None, None) in _offers(db, "dragon-shrine", "gift_pokemon")
    assert ("machop", "sitrus-berry", None, None, "abra") in _offers(db, "goldenrod-dept-store-5f", "trade")
    assert ("dodrio", "smoke-ball", None, None, "dragonair") in _offers(db, "blackthorn-emys-house", "trade")
    assert ("magneton", "metal-coat", None, None, "dugtrio") in _offers(db, "power-plant", "trade")


def test_dragon_shrine_does_not_inherit_den_fishing(db: sqlite3.Connection) -> None:
    assert (
        db.execute(
            """SELECT count(*) FROM map_area a JOIN map m ON m.id = a.map_id
           WHERE m.version_group_id = 4 AND m.identifier = 'dragon-shrine'"""
        ).fetchone()[0]
        == 0
    )
    assert ("dratini", None, 15, None, None) in _offers(db, "dragon-shrine", "gift_pokemon")


def test_crystal_battle_tower_rewards(db: sqlite3.Connection) -> None:
    rewards = _offers(db, "battle-tower-1f", "gift_item")
    assert {(row[1], row[2]) for row in rewards} == {
        ("hp-up", 5),
        ("protein", 5),
        ("iron", 5),
        ("carbos", 5),
        ("calcium", 5),
    }


def test_crystal_game_corner_prizes(db: sqlite3.Connection) -> None:
    prizes = _offers(db, "goldenrod-game-corner", "prize_pokemon")
    assert {(row[0], row[2], row[3]) for row in prizes} == {
        ("abra", 5, 100),
        ("cubone", 15, 800),
        ("wobbuffet", 15, 1500),
    }
    prizes = _offers(db, "celadon-game-corner-prize-room", "prize_pokemon")
    assert {(row[0], row[2], row[3]) for row in prizes} == {
        ("pikachu", 25, 2222),
        ("porygon", 15, 5555),
        ("larvitar", 40, 8888),
    }


def test_crystal_suicune_is_static_and_only_two_beasts_roam(db: sqlite3.Connection) -> None:
    assert db.execute(
        """SELECT min_level, max_level FROM encounter e JOIN encounter_method m ON m.id = e.method_id
           WHERE version_id = 6 AND pokemon_id = 245 AND m.identifier = 'static'"""
    ).fetchall() == [(40, 40)]
    assert db.execute(
        """SELECT p.identifier FROM encounter e JOIN encounter_method m ON m.id = e.method_id
           JOIN pokemon p ON p.id = e.pokemon_id WHERE version_id = 6 AND m.identifier = 'roaming-grass'
           ORDER BY p.id"""
    ).fetchall() == [("raikou",), ("entei",)]
    assert db.execute(
        """SELECT o.level FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = 4 AND m.identifier = 'tin-tower-1f' AND o.pokemon_id = 245"""
    ).fetchall() == [(40,)]


@pytest.mark.parametrize("kind", ["move_tutor", "point_prize"])
@pytest.mark.parametrize("price", [0, -1, None])
def test_crystal_offers_reject_missing_or_invalid_price(db: sqlite3.Connection, kind: str, price: int | None) -> None:
    try:
        db.execute("UPDATE npc_offer SET price = ? WHERE kind = ?", (price, kind))
        query = next(query for name, query in CHECKS if name == "offre de personnage incohérente")
        assert db.execute(query).fetchall()
    finally:
        db.rollback()
