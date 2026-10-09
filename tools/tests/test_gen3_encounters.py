"""Rencontres et terrains des cinq versions GBA, sur leurs sources épinglées."""

from collections import defaultdict
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.compare_wild_gen3 import compare_wild_tables
from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.map_spots import read_spots
from pokemaps_data.maps import ROAMING_AREAS, roaming_areas
from pokemaps_data.maps_layout import identifier, read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_wild import roaming_maps
from pokemaps_data.preview_wild_gen3 import _map_data
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import validate
from spot_editor.catalog import EditorCatalog, EncounterLine, Family
from spot_editor.coverage import PlacementNeeds
from spot_editor.session import SpotSession
from spot_editor.terrain import WildTerrains
from spot_editor.version_choice import VERSION_LABELS

from .conftest import CACHE
from .test_remake_encounters import assert_remake_coverage


def test_all_probabilities_rates_and_versions(gen3_builder: DatabaseBuilder) -> None:
    builder = gen3_builder
    totals: dict[tuple, float] = defaultdict(float)
    for group in builder.encounters.encounter_groups:
        if group.chance is not None:
            totals[(group.version_id, group.location_area_id, group.method_id, group.conditions)] += group.chance
    assert {value for value in totals.values()} == {100}
    assert {key[0] for key in totals} == {7, 8, 9, 10, 11}
    rates = builder.encounters.encounter_rate_table()
    assert all(0 < rate <= 100 for *_, rate in rates)
    assert all(key[:3] in {row[:3] for row in rates} for key in totals)


def test_scenario_conditions_and_default_blue_option(gen3_builder: DatabaseBuilder) -> None:
    b = gen3_builder
    identifiers = {int(row["id"]): row["identifier"] for row in b.api.table("encounter_condition_values")}
    safari = b.locations.area_ids["hoenn-safari-zone/expansion-north"]
    rows = [row for row in b.encounters.encounter_groups if row.location_area_id == safari]
    assert rows and all({identifiers[c] for c in row.conditions} == {"story-progress-hall-of-fame"} for row in rows)
    isle = b.locations.area_ids["five-island"]
    rows = [row for row in b.encounters.encounter_groups if row.location_area_id == isle]
    assert rows and all(
        {identifiers[c] for c in row.conditions} == {"story-progress-hall-of-fame", "story-progress-national-dex"}
        for row in rows
    )
    latias = [
        row
        for row in b.encounters.encounter_groups
        if row.version_id == 9
        and row.pokemon_id == 380
        and b.encounters.method_identifiers[row.method_id].startswith("roaming")
    ]
    assert latias and all("tv-option-red" in {identifiers[c] for c in row.conditions} for row in latias)
    latios = [
        row
        for row in b.encounters.encounter_groups
        if row.version_id == 9
        and row.pokemon_id == 381
        and b.encounters.method_identifiers[row.method_id].startswith("roaming")
    ]
    assert latios and all("tv-option-blue" in {identifiers[c] for c in row.conditions} for row in latios)


def test_comparison_reports_differences_and_agreement(gen3_builder: DatabaseBuilder) -> None:
    differences = compare_wild_tables(gen3_builder)
    assert differences
    assert not any(row.area == "hoenn-route-101" for row in differences)
    assert any(row.area == "mt-ember/summit-path-3f" and not row.pokeapi and row.pret for row in differences)
    assert any(row.area == "hoenn-altering-cave" and row.pokeapi and not row.pret for row in differences)


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_roaming_routes_and_editor_regions(game: Game, source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    maps = Gen3GameMaps(repo, game, read_layout_curation())
    routes = roaming_maps(repo)
    assert len(routes) == (25 if repo.remake else 20)
    assert all(repo.maps[const].is_outdoor and const in maps.placements for const in routes)
    assert roaming_areas(maps)[: len(routes)] == [(const, ROAMING_AREAS[game.map_family]) for const in routes]
    assert game.version_group in VERSION_LABELS
    assert set(maps.world_region.values()) >= ({"KANTO", "SEVII"} if repo.remake else {"HOENN"})


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_terrain_placement_and_editor_consistency(game: Game, assets: Path, source_cache_ready: None) -> None:
    data = _map_data(assets / "maps" / game.version_group, pret_dir(CACHE, game.pret_repo), game)
    assert data.spots
    assert all((spot.x, spot.y) in data.terrain[(identifier(spot.map_const), spot.kind)] for spot in data.spots)
    terrains = WildTerrains(CACHE)
    family = Family(game.map_family, game.version_group, (game.version_group,))
    const = "MAP_ROUTE1" if game.pret_repo == "pokefirered" else "MAP_ROUTE101"
    key = identifier(const)
    assert terrains.kinds(family, key) == {"grass"}
    assert terrains.points(family, key, "grass") == data.terrain[(key, "grass")]
    assert terrains.region(family, key) == ("kanto" if game.pret_repo == "pokefirered" else "hoenn")
    rock = "MAP_ROCK_TUNNEL_B1F" if game.pret_repo == "pokefirered" else "MAP_ROUTE111"
    assert terrains.points(family, identifier(rock), "rock")
    if game.pret_repo != "pokefirered":
        assert not terrains.points(family, identifier("MAP_SHOAL_CAVE_LOW_TIDE_ENTRANCE_ROOM"), "water")
        assert terrains.points(family, identifier("MAP_SHOAL_CAVE_HIGH_TIDE_ENTRANCE_ROOM"), "water")


def test_editor_accepts_underwater_encounters() -> None:
    line = EncounterLine("Émeraude", "seaweed", "Plongée", 366, "Coquiperl", 20, 30, 65)
    assert line.terrains == ("underwater",)


def test_preview_can_be_browsed(gen3_builder: DatabaseBuilder, tmp_path: Path, assets: Path) -> None:
    data = {
        game.version_group: _map_data(assets / "maps" / game.version_group, pret_dir(CACHE, game.pret_repo), game)
        for game in GEN3_GAMES
    }
    b = DatabaseBuilder(gen3_builder.api, GEN3_GAMES, data, gen3_builder.pret_roots)
    for current in data.values():
        current.areas = [
            (const, key) for const, key in current.areas if b.locations.area_ids[key] in b.encounters.used_areas
        ]
    path = tmp_path / "preview.db"
    b.write(path, set())
    assert validate(path) == []
    catalog = EditorCatalog(path)
    try:
        missing = catalog.connection.execute(
            """SELECT DISTINCT v.identifier, e.location_area_id, method.identifier
               FROM encounter e JOIN version v ON v.id = e.version_id
               JOIN encounter_method method ON method.id = e.method_id WHERE method.is_one_off = 0
               AND NOT EXISTS (SELECT 1 FROM map_area ma JOIN map m ON m.id = ma.map_id
                 JOIN map_spot s ON s.map_id = ma.map_id
                 WHERE ma.location_area_id = e.location_area_id AND m.version_group_id = v.version_group_id
                   AND ((method.identifier = 'walk' AND s.kind IN ('grass', 'floor'))
                     OR (method.identifier = 'rock-smash' AND s.kind = 'rock')
                     OR (method.identifier = 'seaweed' AND s.kind = 'underwater')
                     OR (method.identifier IN ('surf', 'old-rod', 'good-rod', 'super-rod')
                         AND s.kind = 'water')))"""
        ).fetchall()
        assert missing == []
        families = catalog.families()
        assert {family.identifier for family in families} == {"ruby-sapphire-emerald", "firered-leafgreen"}
        for family in families:
            assert catalog.maps(family)
            assert set(catalog.world_names(family)) >= (
                {"kanto", "sevii"} if family.identifier == "firered-leafgreen" else {"hoenn"}
            )
        _check_hoenn_editor_methods(catalog)
        _check_hoenn_coverage(catalog)
        assert_remake_coverage(catalog)
    finally:
        catalog.connection.close()


def _check_hoenn_editor_methods(catalog: EditorCatalog) -> None:
    for game in GEN3_GAMES:
        if game.map_family != "ruby-sapphire-emerald":
            continue
        repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
        family = Family(game.map_family, game.version_group, (game.version_group,))
        found = catalog.maps(family)
        assert all(current.identifier != "seafloor-cavern-room9" for current in found)
        for current in found:
            const = "MAP_" + current.identifier.upper().replace("-", "_")
            methods = {line.method for line in catalog.encounters(current)}
            assert methods == repo.wild_methods[const], (game.version_group, const, methods)


def _check_hoenn_coverage(catalog: EditorCatalog) -> None:
    families = [family for family in catalog.families() if family.identifier == "ruby-sapphire-emerald"]
    needs = PlacementNeeds(catalog, families, WildTerrains(CACHE))
    shortfalls = needs.shortfalls(SpotSession(read_spots()))
    assert all(not row.blocking for row in shortfalls)
    actual = {(row.key.map_identifier, row.key.kind, row.version_group, row.points, row.required) for row in shortfalls}
    # Décisions de place relues dans docs/generations/rencontres-hoenn.md ; aucun autre manque n'est admis.
    shared = {
        (name, kind, group, points, required)
        for group in ("ruby-sapphire", "emerald")
        for name, kind, points, required in (
            ("dewford-town", "water", 5, 6),
            ("route102", "water", 3, 5),
            ("route115", "grass", 2, 5),
        )
    }
    ruby = {
        (name, "water", "ruby-sapphire", points, required)
        for name, points, required in (
            ("abandoned-ship-hidden-floor-corridors", 1, 5),
            ("abandoned-ship-rooms-b1f", 1, 5),
            ("meteor-falls-b1f-2r", 5, 6),
        )
    }
    assert actual == shared | ruby
