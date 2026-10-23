"""Relecture des extractions de la phase 7 contre le dépôt HGSS épinglé."""

from pathlib import Path

import pytest

from pokemaps_data.activities_hgss import _voltorb
from pokemaps_data.guides_hgss import guide_catalog, map_entries, weekly_calendar
from pokemaps_data.pokewalker_hgss import walker_catalog
from pokemaps_data.pret_gen4_source import read_json
from pokemaps_data.preview_characters_hgss import check_characters
from pokemaps_data.preview_content_hgss import CONTRACT, check_content
from pokemaps_data.sources_characters_hgss import source_digest

pytestmark = pytest.mark.pipeline
ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / ".cache/hgss-qualification"


def test_pinned_content_source_inventory() -> None:
    for name, expected in read_json(CONTRACT)["native"].items():
        assert source_digest(NATIVE / name) == expected, name


def test_native_pokewalker_courses_and_voltorb_configurations() -> None:
    courses = walker_catalog(NATIVE)["courses"]
    assert len(courses) == 27
    assert [r["watts"] for r in courses[:9]] == [0, 0, 50, 200, 500, 1000, 2000, 3000, 5000]
    assert courses[0]["pokemon"][0]["species"] == 115
    assert courses[0]["pokemon"][0]["steps"] == 3000
    assert courses[0]["items"][0] == dict(item=28, steps=2500, weight=20)
    assert all(r["national"] for r in courses[8:20])
    assert all(r["access"] == "external_accessory" for r in courses[20:])
    boards = _voltorb(NATIVE)["configurations"]
    assert boards[0]["payout"] == 24
    assert boards[-1]["level"] == 8


def test_snapshot_links_and_preview_match_native_prerequisites() -> None:
    characters = check_characters(ROOT / "build/preview/hgss-characters")
    content = check_content(ROOT / "build/preview/hgss-content")
    assert guide_catalog(characters, map_entries()) == content["guides"]
    assert weekly_calendar(characters) == content["weekly"]
    assert content == read_json(CONTRACT.with_name("contenus-hgss-catalogue.json"))
