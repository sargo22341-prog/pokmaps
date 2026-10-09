"""Lecture autonome du JSON GBA et erreurs bloquantes à la frontière des sources."""

import json
from pathlib import Path

import pytest

from pokemaps_data import maps
from pokemaps_data.builder_wild_gen3 import _area_key, _conditions
from pokemaps_data.games import EMERALD, FIRERED_LEAFGREEN, RUBY_SAPPHIRE
from pokemaps_data.map_spots import TerrainKey, read_spots, write_spots
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_wild import wild_tables
from pokemaps_data.preview_wild_gen3 import build_wild_preview


def _source(root: Path) -> dict:
    fields = [
        {"type": "land_mons", "encounter_rates": [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]},
        {"type": "water_mons", "encounter_rates": [60, 30, 5, 4, 1]},
        {"type": "rock_smash_mons", "encounter_rates": [60, 30, 5, 4, 1]},
        {
            "type": "fishing_mons",
            "encounter_rates": [70, 30, 60, 20, 20, 40, 40, 15, 4, 1],
            "groups": {"old_rod": [0, 1], "good_rod": [2, 3, 4], "super_rod": [5, 6, 7, 8, 9]},
        },
    ]
    encounters = []
    for suffix, species in (("Ruby", "SEEDOT"), ("Sapphire", "LOTAD")):
        entry = {"map": "MAP_ROUTE102", "base_label": "Route102_" + suffix}
        for field in fields:
            entry[field["type"]] = {
                "encounter_rate": 20,
                "mons": [
                    {"species": "SPECIES_" + species, "min_level": 3, "max_level": 5} for _ in field["encounter_rates"]
                ],
            }
        encounters.append(entry)
    result = {
        "wild_encounter_groups": [
            {"label": "gWildMonHeaders", "for_maps": True, "fields": fields, "encounters": encounters}
        ]
    }
    _write(root, result)
    return result


def _write(root: Path, data: dict) -> None:
    path = root / "src/data/wild_encounters.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_versions_rods_and_engine_probabilities(tmp_path: Path) -> None:
    _source(tmp_path)
    repo = Gen3PretRepo(tmp_path, RUBY_SAPPHIRE.pret_versions)
    for version, species in (("ruby", "SEEDOT"), ("sapphire", "LOTAD")):
        tables = wild_tables(repo, version)
        assert {t.method for t in tables} == {"walk", "surf", "rock-smash", "old-rod", "good-rod", "super-rod"}
        assert {slot.species for table in tables for slot in table.slots} == {species}
        assert all(sum(slot.chance for slot in table.slots) == 100 for table in tables)
        assert {table.rate for table in tables} == {20}
        rods = {table.method: tuple(slot.chance for slot in table.slots) for table in tables}
        assert rods["old-rod"] == (70, 30)
        assert rods["good-rod"] == (60, 20, 20)
        assert rods["super-rod"] == (40, 40, 15, 4, 1)


@pytest.mark.parametrize("problem", ["rates", "slots", "level", "method", "suffix", "group", "duplicate"])
def test_invalid_sources_fail_with_the_source_name(tmp_path: Path, problem: str) -> None:
    data = _source(tmp_path)
    group = data["wild_encounter_groups"][0]
    entry = group["encounters"][0]
    match problem:
        case "rates":
            group["fields"][0]["encounter_rates"][0] = 19
        case "slots":
            entry["land_mons"]["mons"].pop()
        case "level":
            entry["land_mons"]["mons"][0]["min_level"] = 0
        case "method":
            entry["unknown_mons"] = entry["land_mons"]
        case "suffix":
            entry["base_label"] = "Route102_Unknown"
        case "group":
            group["label"] = "UnknownHeaders"
        case "duplicate":
            group["encounters"].append(entry)
        case _:
            raise AssertionError(problem)
    _write(tmp_path, data)
    with pytest.raises(ValueError, match=r"wild_encounters\.json"):
        wild_tables(Gen3PretRepo(tmp_path, RUBY_SAPPHIRE.pret_versions), "ruby")


def test_missing_or_ambiguous_area_fails(tmp_path: Path) -> None:
    _source(tmp_path)
    table = wild_tables(Gen3PretRepo(tmp_path, RUBY_SAPPHIRE.pret_versions), "ruby")[0]
    for areas in ({}, {"MAP_ROUTE102": ["hoenn-route-102", "hoenn-route-103"]}):
        with pytest.raises(ValueError, match=r"map_areas\.csv"):
            _area_key(table, areas)


def test_story_requirements_are_distinct_between_branches() -> None:
    assert _conditions(EMERALD, "MAP_SAFARI_ZONE_NORTHEAST") == ("story-progress-hall-of-fame",)
    assert _conditions(EMERALD, "MAP_SAFARI_ZONE_NORTH") == ()
    assert _conditions(RUBY_SAPPHIRE, "MAP_SAFARI_ZONE_NORTHWEST") == ()
    assert _conditions(FIRERED_LEAFGREEN, "MAP_FIVE_ISLAND") == (
        "story-progress-hall-of-fame",
        "story-progress-national-dex",
    )
    assert _conditions(FIRERED_LEAFGREEN, "MAP_THREE_ISLAND") == ()


def test_editor_can_save_the_new_families_before_android_activation(tmp_path: Path) -> None:
    spots = {
        TerrainKey("ruby-sapphire-emerald", "route101", "grass", "emerald"): frozenset({(8, 8)}),
        TerrainKey("firered-leafgreen", "route1", "grass"): frozenset({(24, 24)}),
    }
    path = tmp_path / "map_spots.csv"
    write_spots(spots, path)
    assert read_spots(path) == spots


def test_scoped_areas_replace_common_areas(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "map_areas.csv").write_text(
        "family,map,location_area,note,version_group\n"
        "ruby-sapphire-emerald,MAP_SAFARI_ZONE_NORTHEAST,hoenn-safari-zone/neacro-bike-area,commun\n"
        "ruby-sapphire-emerald,MAP_SAFARI_ZONE_NORTHEAST,hoenn-safari-zone/expansion-north,extension,emerald\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(maps, "DATA_DIR", tmp_path)
    assert maps.read_map_areas("ruby-sapphire")["ruby-sapphire-emerald"] == [
        ("MAP_SAFARI_ZONE_NORTHEAST", "hoenn-safari-zone/neacro-bike-area")
    ]
    assert maps.read_map_areas("emerald")["ruby-sapphire-emerald"] == [
        ("MAP_SAFARI_ZONE_NORTHEAST", "hoenn-safari-zone/expansion-north")
    ]


@pytest.mark.parametrize("relative", [".", "preview", ".."])
def test_preview_cannot_overwrite_source_assets(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError, match="séparé des assets"):
        build_wild_preview(tmp_path / "cache", tmp_path / "assets", tmp_path / "assets" / relative)
