"""Contrats des trois versions Sinnoh distribuées, sans dépendance aux aperçus ni au réseau."""

import csv
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from pokemaps_data.games import GEN4_GAMES, Game
from pokemaps_data.maps import GameMapData
from pokemaps_data.validate import CHECKS
from pokemaps_data.validate_maps_gen4 import check_inventory, validate_catalog

_ASSETS = Path(__file__).parents[2] / "app/src/main/assets"


@pytest.mark.pipeline
@pytest.mark.parametrize("game", GEN4_GAMES, ids=lambda game: game.version_group)
def test_source_export_positions_are_valid(game: Game, sinnoh_exports: Callable[[Game], GameMapData]) -> None:
    data = sinnoh_exports(game)
    regions = {row.const: row for row in data.maps}
    assert data.characters_complete
    assert data.objects and data.warps
    for obj in [*data.objects, *data.warps]:
        region = regions[obj.map_const]
        assert region.x <= obj.x <= region.x + region.width, (obj, region)
        assert region.y <= obj.y <= region.y + region.height, (obj, region)
    passages = {(w.map_const, w.x, w.y) for w in data.warps}
    assert all((o.map_const, o.x, o.y) not in passages for o in data.objects if o.kind in {"npc", "trainer"})


def test_sinnoh_metadata_preserves_its_hashes_across_git_checkouts() -> None:
    for game in GEN4_GAMES:
        folder = _ASSETS / "maps" / game.version_group
        for path in folder.iterdir():
            if path.suffix in {".json", ".tsv", ".sha256"}:
                assert b"\r\n" not in path.read_bytes(), path


def test_sinnoh_versions_and_regional_dexes(db: sqlite3.Connection) -> None:
    versions = db.execute(
        """SELECT v.id, v.identifier, vg.generation_id FROM version v
           JOIN version_group vg ON vg.id = v.version_group_id WHERE vg.generation_id = 4 ORDER BY v.id"""
    ).fetchall()
    assert versions == [(12, "diamond", 4), (13, "pearl", 4), (14, "platinum", 4)]
    for group, regional in ((8, 151), (9, 210)):
        counts = db.execute(
            """SELECT p.identifier, count(*) FROM version_group_pokedex vp JOIN pokedex p ON p.id = vp.pokedex_id
               JOIN pokedex_entry pe ON pe.pokedex_id = p.id WHERE vp.version_group_id = ? GROUP BY p.id""",
            (group,),
        ).fetchall()
        assert sorted(count for _, count in counts) == [regional, 493]


def test_sinnoh_map_catalogs_are_distributed_and_complete(db: sqlite3.Connection) -> None:
    for game in GEN4_GAMES:
        folder = _ASSETS / "maps" / game.version_group
        check_inventory(folder)
        validate_catalog(folder)
        with (folder / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
            catalog = list(csv.DictReader(handle, delimiter="\t"))
        count = db.execute(
            """SELECT count(*) FROM map m JOIN version_group vg ON vg.id = m.version_group_id
               WHERE vg.identifier = ?""",
            (game.version_group,),
        ).fetchone()[0]
        assert count == len(catalog)
        assert any(row["const"] == "SINNOH" for row in catalog)


def test_sinnoh_characters_teams_passages_and_shard_costs_exist(db: sqlite3.Connection) -> None:
    for group in (8, 9):
        for table in ("map_warp", "map_object", "map_spot"):
            count = db.execute(
                f"SELECT count(*) FROM {table} c JOIN map m ON m.id = c.map_id WHERE m.version_group_id = ?",
                (group,),
            ).fetchone()[0]
            assert count > 100, (group, table)
    assert db.execute("SELECT count(*) FROM npc_offer_component WHERE kind = 'cost'").fetchone()[0] > 0
    assert db.execute("SELECT count(*) FROM npc_offer_component WHERE kind = 'extra'").fetchone()[0] > 0


@pytest.mark.parametrize("column,value", [("kind", "unknown"), ("quantity", 0), ("item_id", -1)])
def test_invalid_offer_components_are_rejected(db: sqlite3.Connection, column: str, value: str | int) -> None:
    db.execute(
        f"UPDATE npc_offer_component SET {column} = ? WHERE rowid = (SELECT min(rowid) FROM npc_offer_component)",
        (value,),
    )
    db.commit()
    query = next(query for label, query in CHECKS if label == "composant d'offre invalide")
    assert db.execute(query).fetchall()
