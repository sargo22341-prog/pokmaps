"""Particularités de Hoenn relues sur les sources épinglées et l'aperçu de phase 4."""

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import EMERALD, RUBY_SAPPHIRE, Game
from pokemaps_data.map_spots import TerrainKey, read_spots, write_spots
from pokemaps_data.maps_layout import read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_hoenn_caves import moving_cave_areas
from pokemaps_data.pret_hoenn_facilities import facility_series, validate_facility_series
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import CHECKS
from spot_editor.catalog import EncounterLine, required_spots

from .conftest import CACHE


def test_dive_is_a_distinct_editor_terrain(tmp_path: Path) -> None:
    line = EncounterLine("Émeraude", "seaweed", "Plongée", 366, "Coquiperl", 20, 35, 65)
    assert required_spots([line], "underwater") == 1
    assert required_spots([line], "water") == 0
    points = {TerrainKey("ruby-sapphire-emerald", "underwater-route124", "underwater"): frozenset({(8, 8)})}
    path = tmp_path / "map_spots.csv"
    write_spots(points, path)
    assert read_spots(path) == points


def test_database_accepts_dive_and_rejects_unknown_terrain(db: sqlite3.Connection) -> None:
    query = next(query for description, query in CHECKS if description == "emplacement de Pokémon hors de sa carte")
    spot = db.execute("SELECT id FROM map_spot LIMIT 1").fetchone()[0]
    db.execute("UPDATE map_spot SET kind = 'underwater' WHERE id = ?", (spot,))
    assert db.execute(query).fetchall() == []
    db.execute("UPDATE map_spot SET kind = 'unknown' WHERE id = ?", (spot,))
    assert (spot,) in db.execute(query).fetchall()


@pytest.mark.parametrize("game", (EMERALD, RUBY_SAPPHIRE), ids=lambda game: game.version_group)
def test_underwater_only_on_encounter_algues(game: Game, source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    maps = Gen3GameMaps(repo, game, read_layout_curation())
    diving = [const for const, methods in repo.wild_methods.items() if "seaweed" in methods]
    # Seuls les dessous des Routes 124 et 126 ont une table sauvage ; les autres restent sans rencontres.
    assert len(diving) == 2
    for const in diving:
        cells = maps.cells(const)
        assert cells["underwater"] and not cells["water"]
        assert maps.maps[const].map_type == "MAP_TYPE_UNDERWATER"
        assert maps.free_cells(const)["underwater"]


def test_moving_caves_routes_are_read_from_the_engine(source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, EMERALD.pret_repo), EMERALD.pret_versions)
    areas = moving_cave_areas(repo)
    assert {const for const, key in areas if key == "terra-cave/area"} == {
        "MAP_ROUTE114",
        "MAP_ROUTE115",
        "MAP_ROUTE116",
        "MAP_ROUTE118",
    }
    assert {const for const, key in areas if key == "marine-cave/area"} == {
        "MAP_ROUTE105",
        "MAP_ROUTE125",
        "MAP_ROUTE127",
        "MAP_ROUTE129",
    }
    assert moving_cave_areas(Gen3PretRepo(pret_dir(CACHE, RUBY_SAPPHIRE.pret_repo), RUBY_SAPPHIRE.pret_versions)) == ()


def test_moving_caves_reject_inconsistent_engine_tables(tmp_path: Path) -> None:
    path = tmp_path / "src/field_specials.c"
    path.parent.mkdir()
    path.write_text("sAbnormalWeatherMapNumbers[] = { MAP_NUM(MAP_ROUTE114) };", encoding="utf-8")
    with pytest.raises(ValueError, match=r"field_specials\.c"):
        moving_cave_areas(Gen3PretRepo(tmp_path, EMERALD.pret_versions))


def test_special_encounters_and_league_conditions(gen3_builder: DatabaseBuilder) -> None:
    b = gen3_builder
    conditions = {int(row["id"]): row["identifier"] for row in b.api.table("encounter_condition_values")}
    specials = [row for row in b.encounters.encounter_groups if row.version_id in (7, 8, 9)]
    for row in specials:
        area = b.locations.area_keys[row.location_area_id]
        method = b.encounters.method_identifiers[row.method_id]
        if area in {"terra-cave/area", "marine-cave/area"}:
            assert "story-progress-hall-of-fame" in {conditions[value] for value in row.conditions}
            assert row.min_level == row.max_level == 70
            assert any("Entrée variable" in note for note in row.notes)
        if method == "feebas-tile-fishing":
            assert (row.min_level, row.max_level, row.chance) == (20, 25, None)
            assert any("impossibles à placer" in note for note in row.notes)
        if method in {"devon-scope", "wailmer-pail"}:
            assert row.notes and row.chance is None
        if method == "wailmer-pail":
            assert "story-progress-hall-of-fame" in {conditions[value] for value in row.conditions}
    roamers = {
        (row.version_id, row.pokemon_id)
        for row in specials
        if b.encounters.method_identifiers[row.method_id].startswith("roaming")
    }
    assert roamers == {(7, 381), (8, 380), (9, 380), (9, 381)}
    metamo = [row for row in specials if b.locations.area_keys[row.location_area_id].startswith("hoenn-altering-cave/")]
    assert len(metamo) == 9
    for row in metamo:
        assert "story-progress-hall-of-fame" in {conditions[value] for value in row.conditions}
        ordinary = b.locations.area_keys[row.location_area_id].endswith("/a")
        assert ("Événement externe" in row.notes) != ordinary
        if ordinary:
            assert row.pokemon_id == 41


def test_facilities_are_stored_offline_and_validated(assets: Path, tmp_path: Path) -> None:
    source = assets / "maps/emerald"
    validate_facility_series(source)
    data = json.loads((source / "facility_encounters.json").read_text(encoding="utf-8"))
    assert "non capturables" in data["note"]
    data["series"][0]["pokemon"].pop()
    (tmp_path / "facility_encounters.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="emplacements de combat"):
        validate_facility_series(tmp_path)


def test_facilities_use_real_c_species_instead_of_json_indices(assets: Path, source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, EMERALD.pret_repo), EMERALD.pret_versions)
    rows = facility_series(repo)
    assert len(rows) == 48
    assert rows[0].pokemon[0].species == "plusle"
    assert rows[0].pokemon[0].level_parameter == 35
    assert rows[20].pokemon[0].species == "plusle"
    assert rows[20].pokemon[0].level_parameter == 15
    assert rows[40].pokemon[0].species == "seviper"
    stored = json.loads((assets / "maps/emerald/facility_encounters.json").read_text(encoding="utf-8"))
    assert stored["series"] == json.loads(json.dumps([asdict(row) for row in rows]))
