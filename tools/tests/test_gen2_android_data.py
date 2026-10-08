"""Frontière entre les données générées et les fonctionnalités Android de la phase 6."""

import re
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.games import GAMES, GOLD_SILVER
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.validate import CHECKS


def test_gold_silver_is_shipped(db: sqlite3.Connection) -> None:
    assert GOLD_SILVER in GAMES
    assert dict(db.execute("SELECT id, name_fr FROM version WHERE version_group_id = 3")) == {4: "Or", 5: "Argent"}
    assert db.execute("SELECT count(*) FROM pokemon").fetchone()[0] == 251


def test_regions_starts_and_curated_origins_are_exported(db: sqlite3.Connection) -> None:
    assert db.execute(
        """SELECT m.identifier, s.identifier FROM map m JOIN map s ON s.id = m.start_map_id
           WHERE m.version_group_id = 3 AND m.is_world = 1 ORDER BY m.id"""
    ).fetchall() == [("johto", "new-bark-town"), ("kanto", "pallet-town")]
    assert db.execute(
        """SELECT m.identifier, o.identifier FROM map m JOIN map o ON o.id = m.origin_map_id
           WHERE m.identifier IN ('victory-road', 'victory-road-gate') AND m.version_group_id = 3
           ORDER BY m.identifier"""
    ).fetchall() == [("victory-road", "route-26"), ("victory-road-gate", "route-26")]


@pytest.mark.parametrize(
    "assignment",
    ["start_map_id = NULL", "start_map_id = 3999", "origin_map_id = 999999", "is_world = 3"],
)
def test_invalid_region_data_is_rejected(db: sqlite3.Connection, assignment: str) -> None:
    db.execute(f"UPDATE map SET {assignment} WHERE id = 3998")
    query = next(query for name, query in CHECKS if name == "région ou origine de carte invalide")
    assert db.execute(query).fetchall()
    db.rollback()


def _weight_bonus(weight: int) -> int:
    if weight < 1024:
        return -20
    if weight < 2048:
        return 0
    if weight < 3072:
        return 20
    if weight < 4096:
        return 30
    return 40


def test_heavy_ball_categories_match_the_game_weights(db: sqlite3.Connection, gold_silver_repo: Gen2PretRepo) -> None:
    """Le moteur convertit les livres en hectogrammes approximatifs ; aucun seuil ne change avec les poids PokéAPI."""
    weights = dict(db.execute("SELECT identifier, weight_hg FROM pokemon"))
    root = gold_silver_repo.root / "data/pokemon/dex_entries"
    for version in ("gold", "silver"):
        for path in sorted((root / version).glob("*.asm")):
            raw = _dex_weight(path)
            half = raw // 2
            part = half // 16
            converted = half - part - part // 2
            identifier = {"farfetch_d": "farfetchd", "mr__mime": "mr-mime"}.get(path.stem, path.stem.replace("_", "-"))
            assert _weight_bonus(converted) == _weight_bonus(weights[identifier]), path


def _dex_weight(path: Path) -> int:
    match = re.search(r"dw\s+\d+,\s+(\d+)", path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Poids absent du Pokédex : {path}")
    return int(match[1])
