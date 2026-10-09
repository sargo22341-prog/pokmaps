"""Rencontres spécifiques aux remakes : Tanoby, progression, errants et emplacements relus."""

from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import FIRERED_LEAFGREEN
from pokemaps_data.map_spots import read_spots
from pokemaps_data.maps_layout import read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.maps_terrain_gen3 import wild_cells
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_remake_encounters import roaming_starters, unown_chambers
from pokemaps_data.sources import pret_dir
from spot_editor.catalog import EditorCatalog
from spot_editor.coverage import PlacementNeeds
from spot_editor.session import SpotSession
from spot_editor.terrain import WildTerrains
from spot_editor.validation import spot_errors

from .conftest import CACHE


@pytest.fixture
def remake_repo(source_cache_ready: None) -> Gen3PretRepo:
    return Gen3PretRepo(pret_dir(CACHE, FIRERED_LEAFGREEN.pret_repo), FIRERED_LEAFGREEN.pret_versions)


def test_all_tanoby_forms_and_source_order(remake_repo: Gen3PretRepo) -> None:
    rooms = unown_chambers(remake_repo)
    assert [row.map_const.rsplit("_", 2)[-2] for row in rooms] == [
        "MONEAN",
        "LIPTOO",
        "WEEPTH",
        "DILFORD",
        "SCUFIB",
        "RIXY",
        "VIAPOIS",
    ]
    assert rooms[0].letters == (0,) * 11 + (27,)
    assert rooms[-1].letters == (25,) * 11 + (26,)
    assert {value for room in rooms for value in room.letters} == set(range(28))


def test_tanoby_notes_preserve_letters_rates_and_unlock(gen3_builder: DatabaseBuilder) -> None:
    builder = gen3_builder
    rows = [row for row in builder.encounters.encounter_groups if row.version_id in (10, 11) and row.pokemon_id == 201]
    assert len(rows) == 14
    for row in rows:
        assert row.chance == 100 and (row.min_level, row.max_level) == (25, 25)
        assert any("Clé Tanoby avec Force" in note for note in row.notes)
        assert any("Passe Prisme" in note for note in row.notes)
        area = builder.locations.area_keys[row.location_area_id]
        if area == "monean-chamber":
            assert any("A : 99 %, ? : 1 %" in note for note in row.notes)
        if area == "viapos-chamber":
            assert any("Z : 99 %, ! : 1 %" in note for note in row.notes)


def test_remake_roamers_follow_starter_and_sapphire_not_second_league(gen3_builder: DatabaseBuilder) -> None:
    builder = gen3_builder
    identifiers = {int(row["id"]): row["identifier"] for row in builder.api.table("encounter_condition_values")}
    rows = [
        row
        for row in builder.encounters.encounter_groups
        if row.version_id in (10, 11) and builder.encounters.method_identifiers[row.method_id].startswith("roaming")
    ]
    assert len(rows) == 12
    starters = {243: "squirtle", 244: "bulbasaur", 245: "charmander"}
    for row in rows:
        assert {identifiers[value] for value in row.conditions} == {
            "story-progress-hall-of-fame",
            "story-progress-national-dex",
            "starter-" + starters[row.pokemon_id],
        }
        assert (row.min_level, row.max_level, row.chance) == (50, 50, None)
        assert any("Rubis et le Saphir" in note for note in row.notes)
    assert {builder.encounters.method_identifiers[row.method_id] for row in rows} == {"roaming-grass", "roaming-water"}


def test_metamo_events_and_postgame_access(gen3_builder: DatabaseBuilder) -> None:
    builder = gen3_builder
    identifiers = {int(row["id"]): row["identifier"] for row in builder.api.table("encounter_condition_values")}
    groups = [row for row in builder.encounters.encounter_groups if row.version_id in (10, 11)]
    metamo = [
        row for row in groups if builder.locations.area_keys[row.location_area_id].startswith("kanto-altering-cave/")
    ]
    assert len(metamo) == 18
    for row in metamo:
        ordinary = builder.locations.area_keys[row.location_area_id].endswith("/a")
        assert ("Événement externe" in row.notes) != ordinary
        assert {identifiers[value] for value in row.conditions} == {
            "story-progress-hall-of-fame",
            "story-progress-national-dex",
        }
        if ordinary:
            assert row.pokemon_id == 41
    port = [
        row
        for row in groups
        if builder.locations.area_keys[row.location_area_id] == "three-isle-port"
        and builder.encounters.method_identifiers[row.method_id] == "walk"
    ]
    assert port and all(
        {identifiers[value] for value in row.conditions}
        == {"story-progress-hall-of-fame", "story-progress-national-dex"}
        for row in port
    )
    cave = [row for row in groups if builder.locations.area_keys[row.location_area_id].startswith("cerulean-cave/")]
    assert cave and all(any("Rubis et le Saphir" in note for note in row.notes) for row in cave)


def test_remake_encounter_type_overrides_behavior(remake_repo: Gen3PretRepo) -> None:
    current = remake_repo.maps["MAP_ROUTE1"]
    tileset = remake_repo.tilesets[current.layout.primary_tileset]
    tile = next(tile for tile in tileset.metatiles if tile.encounter_type == 1 and tile.behavior == 2)
    remake_repo.tilesets[current.layout.primary_tileset] = replace(
        tileset, metatiles=tuple(replace(tile, behavior=0, encounter_type=1) for _ in tileset.metatiles)
    )
    assert wild_cells(remake_repo, current)["floor"]
    remake_repo.tilesets[current.layout.primary_tileset] = replace(
        tileset, metatiles=tuple(replace(tile, behavior=2, encounter_type=0) for _ in tileset.metatiles)
    )
    assert not wild_cells(remake_repo, current)["grass"]


def test_cycling_road_grass_is_not_cave_floor(remake_repo: Gen3PretRepo) -> None:
    maps = Gen3GameMaps(remake_repo, FIRERED_LEAFGREEN, read_layout_curation())
    cells = maps.cells("MAP_ROUTE17")
    assert cells["grass"] and not cells["floor"]


def test_remake_source_readers_reject_missing_tables(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/wild_encounter.c").write_text("", encoding="utf-8")
    (tmp_path / "src/roamer.c").write_text("", encoding="utf-8")
    repo = Gen3PretRepo(tmp_path, FIRERED_LEAFGREEN.pret_versions)
    with pytest.raises(ValueError, match=r"wild_encounter\.c"):
        unown_chambers(repo)
    with pytest.raises(ValueError, match=r"roamer\.c"):
        roaming_starters(repo, "firered")


def assert_remake_coverage(catalog: EditorCatalog) -> None:
    families = [family for family in catalog.families() if family.identifier == "firered-leafgreen"]
    terrains = WildTerrains(CACHE)
    spots = read_spots()
    session = SpotSession(spots)
    assert spot_errors(session, families, terrains) == []
    places = catalog.maps(families[0])
    assert len(places) == 124
    curated = {key: points for key, points in spots.items() if key.family == "firered-leafgreen"}
    assert len(curated) == 168 and sum(map(len, curated.values())) == 3294
    assert {key.map_identifier for key in curated} == {place.identifier for place in places}
    for key, points in curated.items():
        assert points
        assert all(
            (x - bx) ** 2 + (y - by) ** 2 >= 48**2 for x, y in points for bx, by in points if (x, y) != (bx, by)
        ), key
    shortfalls = PlacementNeeds(catalog, families, terrains).shortfalls(session)
    assert all(not row.blocking for row in shortfalls)
    # Décisions de capacité relues dans docs/generations/rencontres-remake-1g.md.
    assert {(row.key.map_identifier, row.key.kind, row.points, row.required) for row in shortfalls} == {
        ("pallet-town", "water", 2, 8),
        ("celadon-city", "water", 2, 4),
        ("viridian-city", "water", 4, 7),
        ("two-island-cape-brink", "grass", 5, 8),
        ("mt-ember-ruby-path-b1f-stairs", "rock", 1, 2),
        ("mt-ember-ruby-path-b2f-stairs", "rock", 1, 2),
        ("route4", "water", 4, 6),
        ("route11", "water", 5, 6),
        ("route14", "grass", 4, 6),
        ("route16", "grass", 3, 4),
        ("route18", "grass", 4, 5),
        ("route22", "water", 4, 7),
        ("route24", "grass", 5, 7),
        ("route25", "grass", 3, 7),
    }
