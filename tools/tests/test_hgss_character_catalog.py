"""Validation de la phase 5 après génération explicite, sans téléchargement."""

from pathlib import Path

import pytest

from pokemaps_data.preview_characters_hgss import check_characters

pytestmark = pytest.mark.pipeline
PREVIEW = Path(__file__).resolve().parents[1] / "build/preview/hgss-characters"


@pytest.fixture(scope="module")
def catalog() -> dict:
    return check_characters(PREVIEW)


def test_story_battles_have_unique_actors_and_starter_variants(catalog: dict) -> None:
    battles = catalog["resolved_battles"]
    assert len(battles) == 123
    rival = [b for b in battles if b["bank"] == 7]
    assert {(v["starter"], tuple(v["opponents"])) for b in rival for v in b["variants"]} == {
        (152, (286,)),
        (155, (287,)),
        (158, (285,)),
    }
    for battle in battles:
        assert battle["actors"]
        for variant in battle["variants"]:
            assert variant["partner"] not in variant["opponents"]
            if variant["partner"]:
                assert any(a["role"] == "partner" and a["trainer"] == variant["partner"] for a in battle["actors"])


def test_milk_quantities_keep_their_own_prices(catalog: dict) -> None:
    milk = [o for o in catalog["service_steps"] if o["bank"] == 250 and o["values"] and o["values"][0] == 33]
    assert {(tuple(o["values"]), o["costs"][0]["amount"]) for o in milk} == {((33, 1), 500), ((33, 12), 6000)}


def test_calendar_has_sixteen_leaders_and_eight_kanto_badge_league(catalog: dict) -> None:
    calendar = catalog["calendar"]
    assert len(calendar["entries"]) == 63
    leaders = [e for e in calendar["entries"] if e["leader"]]
    assert len(leaders) == 16
    assert all(e["destination"] == "MAP_SAFFRON_FIGHTING_DOJO" for e in leaders)
    assert all(e["registration"] and e["registration"][0]["actors"] for e in leaders)
    assert {e["threshold"] for e in calendar["league"]} == {8}
    assert [u["flag"] for u in calendar["unlocks"]] == [0x97D, 0x97E, 0x97F]


def test_aliases_and_every_useful_actor_have_a_decoded_projected_preview(catalog: dict) -> None:
    actors = catalog["actors"]
    aliases = [a for a in actors if a["alias_of"]]
    assert len(aliases) == 5
    assert all(not a["useful"] for a in aliases)
    assert all(
        any(b["header"] == a["header"] and b["native"]["identity"] == a["alias_of"] for b in actors) for a in aliases
    )
    useful = [a for a in actors if a["useful"]]
    assert len(useful) == catalog["placements"]["count"] == 762
    assert all(a["placement"]["inside"] for a in useful)
    native_height = [a for a in useful if a["placement"]["height_source"] == "event"]
    assert catalog["placements"]["native_height_only"] == 1
    assert [(a["header"], a["native"]["identity"]) for a in native_height] == [(67, "obj_T21_gsrivel")]
    assert native_height[0]["placement"]["height_fx32"] == 0
    bridge = [a for a in useful if a.get("scene_placement", {}).get("surface") == "upper"]
    assert len(bridge) == 2
    assert {a["placement"]["height_fx32"] for a in bridge} == {131072}
    assert all(a["placement"]["map"] == "maps/253/map.png" for a in bridge)
    assert len(catalog["sprites"]) == 100
    assert all(s["status"] == "decoded" for s in catalog["sprites"])
    follower = next(s for s in catalog["sprites"] if s["sprite"] == "SPRITE_FOLLOWER_MON_STATIC_ELECTRODE")
    assert follower["texture"] == "tsure_poke.11"
    assert follower["palette"] == "tsure_poke0"


def test_persistent_services_have_native_costs_and_stages(catalog: dict) -> None:
    services = catalog["services"]
    assert services["mother"]["normal"][0] == dict(item=26, threshold=900, cost=600, quantity=1)
    assert services["mother"]["normal"][-1]["threshold"] == 50000
    assert len(services["mother"]["berries"]) == 17
    assert {b["quantity"] for b in services["mother"]["berries"]} == {5}
    assert services["mother"]["queue_capacity"] == 5
    assert services["scratch_cards"]["cost"] == 1
    assert services["scratch_cards"]["currency"] == "battle_points"
    assert len(services["scratch_cards"]["rewards"]) == 24
    assert services["scratch_cards"]["rewards"][-1] == dict(item=92, quantity=1)
    assert services["fossils"]["delay"] == "leave_and_reenter"
    assert {f["level"] for f in services["fossils"]["offers"]} == {20}
    assert services["relearner"]["payment"] == "after_success"


def test_offer_currencies_and_native_item_names_are_not_confused(catalog: dict) -> None:
    costs = [c for o in catalog["service_steps"] for c in o["costs"]]
    assert {c["currency"] for c in costs} == {"money", "coins", "battle_points", "athlete_points", "item"}
    assert catalog["names"]["items"]["493"] == "Niveau Ball"
    assert len(catalog["athlete_shops"]["daily"]) == 14
    assert sum(len(s["items"]) for s in catalog["athlete_shops"]["data_cards"]) == 27
    assert len(catalog["athlete_shops"]["seals"]) == 7
    assert {item["cost"] for stock in catalog["athlete_shops"]["seals"] for item in stock["items"]} == {100}
    assert catalog["apricorns"]["daily_flag"] == "FLAG_DAILY_KURT_MAKING_BALLS"
    assert len(catalog["trades"]) == 13


def test_every_native_source_reference_exists(catalog: dict) -> None:
    root = PREVIEW.parents[2] / ".cache/hgss-qualification"
    pending = [catalog]
    sources = set()
    for _ in range(1000000):
        if not pending:
            break
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, dict):
            pending.extend(value.values())
            for key, source in value.items():
                if (
                    (key == "source" or key.endswith("_source"))
                    and isinstance(source, str)
                    and source.startswith(("src/", "files/", "include/", "asm/"))
                ):
                    sources.add(source)
    assert not pending, "Catalogue de provenance au-delà de la limite"
    assert sources
    assert not [source for source in sources if not (root / source).is_file()]
