"""Relecture des tables HGSS épinglées, exclusivement lors d'une génération explicite."""

from pathlib import Path

import pytest

from pokemaps_data.character_actors_hgss import actor_catalog
from pokemaps_data.pret_gen4_source import c_defines
from pokemaps_data.pret_hgss_field_items import field_item_tables
from pokemaps_data.pret_hgss_rematches import rematch_catalog
from pokemaps_data.pret_hgss_scripts import battle_sites, read_scripts
from pokemaps_data.pret_hgss_services import apricorn_catalog, shop_catalog, tutor_catalog
from pokemaps_data.pret_hgss_trainers import trainer_catalog
from pokemaps_data.sources_characters_hgss import validate_character_sources

pytestmark = pytest.mark.pipeline
ROOT = Path(__file__).resolve().parents[1] / ".cache/hgss-qualification"


def test_native_character_source_inventory() -> None:
    assert len(validate_character_sources(ROOT)["files"]) == 2416


def test_native_teams_and_phone_series() -> None:
    trainers = trainer_catalog(ROOT)
    rematches = rematch_catalog(ROOT, {row["id"] for row in trainers})
    assert len(trainers) == 737
    assert len(rematches["series"]) == 63
    red = next(row for row in trainers if row["constant"] == "TRAINER_PKMN_TRAINER_RED_RED")
    assert [(mon["species"], mon["level"]) for mon in red["party"]] == [
        (25, 88),
        (131, 80),
        (143, 82),
        (3, 84),
        (6, 84),
        (9, 84),
    ]
    leaders = [row for row in rematches["contacts"] if row["trainerClass"].startswith("TRAINERCLASS_LEADER_")]
    assert len(leaders) == 16
    falkner = next(row for row in leaders if row["id"] == "PHONE_CONTACT_FALKNER")
    assert (falkner["rematchWeekday"], falkner["rematchTimeOfDay"]) == ("RTC_WEEK_SATURDAY", "TIMEOFDAY_WILD_MORN")


def test_native_actor_links_and_items() -> None:
    scripts = read_scripts(ROOT)
    trainers = c_defines(ROOT / "include/constants/trainers.h", "TRAINER_")
    battles = battle_sites(scripts, trainers)
    items = field_item_tables(ROOT, scripts)
    catalog = actor_catalog(ROOT, scripts, battles, items)
    assert len(scripts) == 497
    assert len(battles) == 143
    assert len(catalog["actors"]) == 2392
    assert len(catalog["field_items"]) == 497
    assert items["std_itemball_r29_potion"]["item"] == 17
    assert items["std_itemball_r29_potion"]["quantity"] == 1
    assert items["std_hiddenitem_r29_r30_t21_nugget"]["item"] == 92
    assert all(t in set(trainers.values()) for row in catalog["actors"] for t in row["trainers"])
    multi = next(row for row in battles if row["bank"] == 90 and row["command"] == "MultiBattle")
    assert multi["partner"] == trainers["TRAINER_PKMN_TRAINER_LANCE_LANCE"]
    assert multi["partner"] not in multi["opponents"]


def test_native_prices_tutors_and_apricorns() -> None:
    shops, tutors, apricorns = shop_catalog(ROOT), tutor_catalog(ROOT), apricorn_catalog(ROOT)
    potion = next(row for row in shops["ordinary"] if row["item"] == 17)
    assert (potion["price"], potion["minimum_badges"]) == (300, 0)
    ultra = next(row for row in shops["ordinary"] if row["item"] == 2)
    assert (ultra["price"], ultra["minimum_badges"]) == (1200, 5)
    assert len(shops["special"]) == 30
    headbutt = next(row for row in tutors if row["move"] == "MOVE_HEADBUTT")
    assert (headbutt["cost"], headbutt["currency"]) == (0, "free")
    assert len(tutors) == 52
    assert apricorns["trees"][5]["color"] == "APRICORN_GRN"
    assert apricorns["conversions"][0] == dict(color="APRICORN_RED", item=493, input_quantity=1, output_quantity=1)
