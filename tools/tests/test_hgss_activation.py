"""Contrats des remakes HGSS distribués et de leurs configurations conditionnelles."""

import json
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.application_hgss import validate_assets, validate_database
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import GAMES, HEARTGOLD_SOULSILVER
from pokemaps_data.map_coordinates import editor_offsets
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_evolution_gen4 import compare_ds_evolutions
from spot_editor.catalog import EditorCatalog
from spot_editor.terrain import WildTerrains


def test_hgss_versions_and_native_regional_are_distributed(db: sqlite3.Connection) -> None:
    assert HEARTGOLD_SOULSILVER in GAMES
    assert db.execute("SELECT id, identifier FROM version WHERE version_group_id=10 ORDER BY id").fetchall() == [
        (15, "heartgold"),
        (16, "soulsilver"),
    ]
    assert db.execute("SELECT count(*) FROM pokemon_version_group WHERE version_group_id=10").fetchone()[0] == 493
    assert db.execute("SELECT count(*) FROM pokedex_entry WHERE pokedex_id=7").fetchone()[0] == 256
    worlds = db.execute("SELECT identifier, start_map_id FROM map WHERE version_group_id=10 AND is_world=1").fetchall()
    assert {name for name, _ in worlds} == {"johto", "kanto"}
    assert all(start is not None for _, start in worlds)
    assert validate_database(db) == []


def test_hgss_missing_profile_is_an_error(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM pokemon_version_group WHERE version_group_id=10 AND pokemon_id=493")
    assert validate_database(db) == ["HGSS : profils des 493 espèces HGSS incomplets"]


def test_hgss_distributed_catalogs_and_editor_coordinates(assets: Path) -> None:
    validate_assets(assets)
    offsets = editor_offsets(assets / "maps")
    assert len([key for key in offsets if key[0] == "heartgold-soulsilver"]) == 496
    catalog = EditorCatalog(assets / "database/pokedex.db")
    try:
        family = next(f for f in catalog.families() if f.identifier == "heartgold-soulsilver")
        terrains = WildTerrains(assets.parent, assets / "maps")
        assert terrains.kinds(family, "route-29")
        kind = sorted(terrains.kinds(family, "route-29"))[0]
        point = sorted(terrains.points(family, "route-29", kind))[0]
        assert terrains.snap(family, "route-29", kind, *point) == point
        assert terrains.region(family, "route-29") == "johto"
    finally:
        catalog.close()


def test_hgss_tree_types_do_not_borrow_gsc_names(db: sqlite3.Connection) -> None:
    methods = dict(db.execute("SELECT identifier, name_fr FROM encounter_method WHERE identifier LIKE 'headbutt-%'"))
    assert methods["headbutt-common"] == "Coup d’Boule — arbre commun"
    assert methods["headbutt-rare"] == "Coup d’Boule — arbre rare"
    assert methods["headbutt-secret"] == "Coup d’Boule — arbre particulier"
    assert "headbutt-high" in methods


def test_hgss_safari_has_complete_exclusive_configurations(db: sqlite3.Connection) -> None:
    rows = db.execute("""SELECT DISTINCT cv.identifier FROM encounter_condition_value cv
                         JOIN encounter_condition c ON c.condition_value_id=cv.id
                         JOIN encounter e ON e.id=c.encounter_id WHERE e.version_id=15
                         AND cv.identifier LIKE 'hgss-safari-%'""").fetchall()
    assert len(rows) > 12
    for area in range(12):
        assert (f"hgss-safari-{area}-base",) in rows
    query = """SELECT count(*) FROM npc_offer WHERE kind='fruit_tree' AND map_object_id IN
               (SELECT o.id FROM map_object o JOIN map m ON m.id=o.map_id WHERE m.version_group_id=10)"""
    assert db.execute(query).fetchone()[0] == 31


def test_hgss_transfer_exclusions_are_not_local_objectives(assets: Path, db: sqlite3.Connection) -> None:
    content = json.loads((assets / "hgss.json").read_text(encoding="utf-8"))
    local = {n for row in content["objectives"] for n in row["national"]}
    assert not {377, 378, 379, 387, 390, 393, 479, 480, 481, 482, 485, 486, 488} & local
    assert db.execute("SELECT count(*) FROM pokemon_form WHERE version_id IN (15,16)").fetchone()[0] == 94


def test_hgss_roamers_keep_their_native_region_and_version(db: sqlite3.Connection) -> None:
    rows = db.execute("""SELECT DISTINCT e.version_id, e.pokemon_id, l.region_id, e.min_level
                         FROM encounter e JOIN encounter_method m ON m.id=e.method_id
                         JOIN location_area a ON a.id=e.location_area_id JOIN location l ON l.id=a.location_id
                         WHERE e.version_id IN (15,16) AND m.identifier LIKE 'roaming-%'""").fetchall()
    assert set(rows) == {
        (15, 243, 2, 40),
        (16, 243, 2, 40),
        (15, 244, 2, 40),
        (16, 244, 2, 40),
        (15, 380, 1, 35),
        (16, 381, 1, 35),
    }


def test_hgss_external_events_do_not_become_local_captures(db: sqlite3.Connection) -> None:
    rows = db.execute("""SELECT e.external_event FROM encounter e JOIN location_area a ON a.id=e.location_area_id
                         JOIN location l ON l.id=a.location_id WHERE e.version_id IN (15,16)
                         AND l.identifier='sinjoh-ruins'""").fetchall()
    assert rows and all(row == (1,) for row in rows)
    rows = db.execute("""SELECT e.version_id, e.min_level, e.external_event FROM encounter e
                         JOIN encounter_method m ON m.id=e.method_id WHERE e.version_id IN (15,16)
                         AND e.location_area_id=30117 AND e.pokemon_id=172 AND m.identifier='gift'""").fetchall()
    assert set(rows) == {(15, 30, 1), (16, 30, 1)}


@pytest.mark.pipeline
def test_hgss_native_evolution_conditions_match_the_common_export(source_api: PokeApi) -> None:
    root = Path(__file__).parents[1] / ".cache/hgss-qualification"
    game = HEARTGOLD_SOULSILVER
    builder = DatabaseBuilder(source_api, (game,), pret_roots={game.version_group: root})
    compare_ds_evolutions(builder)
