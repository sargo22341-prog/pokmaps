"""Métadonnées de présentation et capacités horaires des jeux."""

import sqlite3
from pathlib import Path

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import FIRERED_LEAFGREEN, GEN3_GAMES
from pokemaps_data.validate import validate


def test_remake_generation_is_explicit() -> None:
    assert FIRERED_LEAFGREEN.remake_generation == 1
    assert [game.remake_generation for game in GEN3_GAMES] == [None, None, 1]


def test_remake_generation_is_exported(gen3_builder: DatabaseBuilder) -> None:
    rows = {row[1]: row[-1] for row in gen3_builder.version_group_table()}
    assert rows == {"ruby-sapphire": None, "emerald": None, "firered-leafgreen": 1}


def test_invalid_remake_generation_is_rejected(db: sqlite3.Connection, database: Path) -> None:
    db.execute("UPDATE version_group SET remake_generation_id = generation_id")
    db.commit()
    copied_database = Path(db.execute("PRAGMA database_list").fetchone()[2])
    assert copied_database != database
    assert any("génération d'origine du remake invalide" in error for error in validate(copied_database))


def test_game_query_derives_time_from_encounters(db: sqlite3.Connection) -> None:
    source = Path(__file__).parents[2] / "app/src/main/java/org/opensources/pokmaps/data/db/GameDao.kt"
    query = source.read_text(encoding="utf-8").split('"""')[1]
    rows = db.execute(query).fetchall()
    columns = [column[0] for column in db.execute(query).description]
    games = [dict(zip(columns, row, strict=True)) for row in rows]
    assert {game["versionIdentifier"] for game in games if game["hasTimeOfDay"]} == {"gold", "silver", "crystal"}
    db.execute("DELETE FROM encounter_condition")
    assert all(not row[columns.index("hasTimeOfDay")] for row in db.execute(query))
