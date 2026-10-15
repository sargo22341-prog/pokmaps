"""Non-régression : Hoenn après l'introduction avec Brice et Flora."""

import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.games import EMERALD, RUBY_SAPPHIRE, Game
from pokemaps_data.hoenn_character_state import display_event, display_result
from pokemaps_data.maps_actor_positions import clears_passages
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_maps import Gen3Event, Gen3Layout, Gen3Map
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate_hoenn_character_state import validate_hoenn_characters


def _map(label: str) -> Gen3Map:
    layout = Gen3Layout("LAYOUT_TEST", 1, 1, "Primary", "Secondary", (0,), 1, 1, (0,))
    return Gen3Map(
        "MAP_TEST", label, 1, 0, 0, layout, "MAP_TYPE_TOWN", "MAPSEC_TEST", (), (), (), (), (), None, None, ()
    )


def _event(sprite: str, flag: str = "0") -> Gen3Event:
    return Gen3Event("object", 0, 0, 0, (("graphics_id", sprite), ("flag", flag), ("script", "0x0")))


@pytest.mark.parametrize("sprite", ["TRUCK", "MOM"])
def test_outdoor_introduction_actors_are_hidden(sprite: str) -> None:
    assert display_event(_map("LittlerootTown"), _event("OBJ_EVENT_GFX_" + sprite)) is None


@pytest.mark.parametrize("sprite", ["BIRCHS_BAG", "POOCHYENA", "ZIGZAGOON_1", "PROF_BIRCH"])
def test_route101_rescue_is_hidden(sprite: str) -> None:
    assert display_event(_map("Route101"), _event("OBJ_EVENT_GFX_" + sprite)) is None


def test_decorations_are_not_gender_dependent_characters() -> None:
    assert (
        display_event(_map("LittlerootTown_MaysHouse_2F"), _event("OBJ_EVENT_GFX_VAR_0", "FLAG_DECORATION_1")) is None
    )
    unrelated = _event("OBJ_EVENT_GFX_VAR_1", "FLAG_HIDE_EVIL_TEAM")
    assert display_event(_map("Route119"), unrelated) == unrelated


def test_rival_uses_may_and_bike_duplicate_is_hidden() -> None:
    original = _event("OBJ_EVENT_GFX_VAR_0", "FLAG_HIDE_ROUTE_119_RIVAL")
    shown = display_event(_map("Route119"), original)
    assert shown is not None and shown.value("graphics_id") == "OBJ_EVENT_GFX_RIVAL_MAY_NORMAL"
    assert original.value("graphics_id") == "OBJ_EVENT_GFX_VAR_0"
    assert display_event(_map("Route119"), _event("OBJ_EVENT_GFX_VAR_3", "FLAG_HIDE_RIVAL_ON_BIKE_ROUTE119")) is None


def test_house_roles_and_professor_lab_are_retained() -> None:
    mother = _event("OBJ_EVENT_GFX_MOM")
    assert display_event(_map("LittlerootTown_BrendansHouse_1F"), mother) == mother
    assert display_event(_map("LittlerootTown_MaysHouse_1F"), mother) is None
    brendan = _event("OBJ_EVENT_GFX_RIVAL_BRENDAN_NORMAL")
    assert display_event(_map("LittlerootTown_BrendansHouse_2F"), brendan) is None
    professor = _event("OBJ_EVENT_GFX_PROF_BIRCH")
    assert display_event(_map("LittlerootTown_ProfessorBirchsLab"), professor) == professor
    assert display_event(_map("Route103"), professor) is None


def test_distributed_database_has_one_female_rival_per_battle(db: sqlite3.Connection) -> None:
    assert validate_hoenn_characters(db) == []


def test_transient_door_actors_are_hidden_but_permanent_npcs_and_rewards_remain(db: sqlite3.Connection) -> None:
    transient = db.execute(
        """SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version_group g ON g.id = m.version_group_id WHERE g.identifier = 'emerald'
           AND ((m.identifier = 'route104' AND o.name_fr = 'Flora')
           OR (m.identifier = 'rustboro-city' AND o.sprite = 'obj-event-gfx-scientist-1'))"""
    ).fetchall()
    assert transient == []
    permanent = db.execute(
        """SELECT count(*) FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version_group g ON g.id = m.version_group_id WHERE g.identifier = 'emerald'
           AND m.identifier = 'littleroot-town-mays-house-2f' AND o.name_fr = 'Flora'"""
    ).fetchone()[0]
    assert permanent == 1
    point = db.execute(
        """SELECT o.x, o.y FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version_group g ON g.id = m.version_group_id WHERE g.identifier = 'emerald'
           AND m.identifier = 'littleroot-town-mays-house-2f' AND o.name_fr = 'Flora'"""
    ).fetchone()
    warps = db.execute(
        """SELECT w.x, w.y FROM map_warp w JOIN map m ON m.id = w.map_id
           JOIN version_group g ON g.id = m.version_group_id WHERE g.identifier = 'emerald'
           AND m.identifier = 'littleroot-town-mays-house-2f'"""
    ).fetchall()
    assert clears_passages(tuple(point), {tuple(warp) for warp in warps})
    rewards = db.execute(
        """SELECT count(*) FROM npc_offer f JOIN map_object o ON o.id = f.map_object_id
           JOIN map m ON m.id = o.map_id JOIN version_group g ON g.id = m.version_group_id
           WHERE g.identifier = 'emerald' AND m.identifier = 'lavaridge-town' AND o.name_fr = 'Flora'"""
    ).fetchone()[0]
    assert rewards > 0


@pytest.mark.parametrize("route", [111, 118, 120])
@pytest.mark.parametrize("sprite", ["CAMERAMAN", "REPORTER_F"])
@pytest.mark.parametrize("prefix", ["FLAG_HIDE_GABBY_AND_TY_ROUTE", "FLAG_HIDE_ROUTE_"])
def test_reporter_rematches_reuse_one_pair(route: int, sprite: str, prefix: str) -> None:
    current = _map(f"Route{route}")
    flag = f"{prefix}{route}" + ("_GABBY_AND_TY" if prefix == "FLAG_HIDE_ROUTE_" else "")
    first = _event(f"OBJ_EVENT_GFX_{sprite}", flag + "_1")
    assert display_event(current, first) == first
    for stage in (2, 3):
        assert display_event(current, _event(f"OBJ_EVENT_GFX_{sprite}", f"{flag}_{stage}")) is None
    unrelated = _event(f"OBJ_EVENT_GFX_{sprite}", "FLAG_HIDE_OTHER_REPORTER")
    assert display_event(current, unrelated) == unrelated


def test_validation_detects_missing_or_repeated_reporters(db: sqlite3.Connection) -> None:
    with closing(sqlite3.connect(":memory:")) as copy:
        db.backup(copy)
        copy.execute(
            "UPDATE map_object SET sprite = 'obj-event-gfx-cameraman' WHERE sprite = 'obj-event-gfx-reporter-f'"
        )
        errors = validate_hoenn_characters(copy)
        assert any("2 journalistes" in error for error in errors)
        assert any("0 journalistes" in error for error in errors)


@pytest.mark.parametrize("group", ["ruby-sapphire", "emerald"])
def test_reporter_rematches_remain_in_source_catalog(assets: Path, group: str) -> None:
    catalog = json.loads((assets / "maps" / group / "characters.json").read_text(encoding="utf-8"))
    for route, count in ((111, 6), (118, 6), (120, 4)):
        actors = [
            actor
            for actor in catalog["characters"]
            if actor["version"] == ("ruby" if group == "ruby-sapphire" else "emerald")
            and actor["key"].startswith(f"Route{route}:")
            and any("GABBY_AND_TY" in str(value) for key, value in actor["event"]["fields"] if key == "flag")
        ]
        assert len(actors) == count
        assert all(actor["result"]["trainers"] for actor in actors)


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_distributed_house_population_matches_boy_hero(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT m.identifier, o.sprite FROM map_object o
           JOIN map m ON m.id = o.map_id JOIN version v ON v.id = o.version_id
           WHERE v.identifier = ? AND m.identifier LIKE 'littleroot-town%' AND o.kind = 'npc'""",
        (version,),
    ).fetchall()
    hero = [sprite for label, sprite in rows if label == "littleroot-town-brendans-house-1f"]
    rival = [sprite for label, sprite in rows if label == "littleroot-town-mays-house-1f"]
    assert hero == ["obj-event-gfx-mom"]
    assert rival == (
        ["obj-event-gfx-woman-4", "obj-event-gfx-ninja-boy"] if version == "emerald" else ["obj-event-gfx-woman-5"]
    )
    assert not any(label == "littleroot-town-brendans-house-2f" for label, _ in rows)
    assert [sprite for label, sprite in rows if label == "littleroot-town-mays-house-2f"] == [
        "obj-event-gfx-rival-may-normal"
    ]
    assert len([sprite for label, sprite in rows if label == "littleroot-town"]) == 3


def test_validation_detects_missing_battles_and_wrong_gender(db: sqlite3.Connection) -> None:
    with closing(sqlite3.connect(":memory:")) as copy:
        db.backup(copy)
        copy.execute("UPDATE map_object SET sprite = 'obj-event-gfx-rival-brendan-normal' WHERE name_fr = 'Flora'")
        assert any("apparence" in error for error in validate_hoenn_characters(copy))
        copy.execute("DELETE FROM map_object WHERE name_fr = 'Flora'")
        assert any("combats affichés" in error for error in validate_hoenn_characters(copy))


@pytest.mark.pipeline
@pytest.mark.parametrize("game", [RUBY_SAPPHIRE, EMERALD])
def test_pinned_trigger_battles_keep_all_starter_variants(game: Game) -> None:
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        reader = repo.offers[version]
        for label in ("Route110", "Route119"):
            current = next(current for current in repo.maps.values() if current.label == label)
            event = next(event for event in current.objects if "RIVAL" in str(event.value("flag")))
            result = display_result(current, event, reader.read_object(event), reader)
            assert sum(trainer.startswith("TRAINER_MAY_") for trainer in result.trainers) == 3
            assert sum(trainer.startswith("TRAINER_BRENDAN_") for trainer in result.trainers) == 3
            if label == "Route119":
                assert any(offer.item in {"ITEM_HM02_FLY", "ITEM_HM_FLY"} for offer in result.offers)


def test_house_movers_and_variable_decorations_do_not_reappear() -> None:
    for house in ("BrendansHouse", "MaysHouse"):
        current = _map(f"LittlerootTown_{house}_1F")
        for sprite in ("MACHOKE_CARRYING_BOX", "MACHOKE_FACING_AWAY", "VIGOROTH_CARRYING_BOX", "VIGOROTH_FACING_AWAY"):
            assert display_event(current, _event("OBJ_EVENT_GFX_" + sprite)) is None
        sibling = _event("OBJ_EVENT_GFX_NINJA_BOY")
        assert (display_event(current, sibling) is None) == (house == "BrendansHouse")
        upstairs = replace(current, label=f"LittlerootTown_{house}_2F")
        assert display_event(upstairs, _event("OBJ_EVENT_GFX_VAR_B", "FLAG_DECORATION_12")) is None
