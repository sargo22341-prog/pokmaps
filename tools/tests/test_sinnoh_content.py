"""Catalogue Sinnoh distribué : données complètes, frontières et liens, sans cache."""

import json
from pathlib import Path

import pytest

from pokemaps_data.sinnoh_catalog import validate_sinnoh_catalog
from pokemaps_data.validate_sinnoh_content import validate_extras


def _catalog(assets: Path) -> dict:
    return json.loads((assets / "sinnoh.json").read_text(encoding="utf-8"))


def test_distributed_sinnoh_content_is_complete(assets: Path) -> None:
    validate_sinnoh_catalog(assets)
    groups = _catalog(assets)["groups"]
    assert groups["diamond-pearl"]["berries"] != []
    assert (
        sorted(groups["diamond-pearl"]["berries"], key=lambda row: row["identifier"]) == groups["platinum"]["berries"]
    )
    assert groups["diamond-pearl"]["moves"] == groups["platinum"]["moves"]
    assert groups["diamond-pearl"]["underground"] == groups["platinum"]["underground"]


def test_berries_keep_ds_growth_yield_and_poffin_ingredients(assets: Path) -> None:
    for value in _catalog(assets)["groups"].values():
        berries = {row["identifier"]: row for row in value["berries"]}
        cheri = berries["cheri-berry"]
        assert (cheri["stage_hours"], cheri["min_yield"], cheri["max_yield"], cheri["drain_rate"]) == (3, 2, 5, 15)
        assert cheri["flavors"] == [10, 0, 0, 0, 0]
        assert berries["chesto-berry"]["flavors"] == [0, 10, 0, 0, 0]
        assert berries["sitrus-berry"]["stage_hours"] == 8
        assert berries["sitrus-berry"]["max_yield"] == 5
        assert berries["belue-berry"]["max_yield"] == 15


def test_super_contests_are_separate_from_hoenn(assets: Path) -> None:
    for value in _catalog(assets)["groups"].values():
        pound = value["moves"][0]
        assert (pound["id"], pound["category"], pound["appeal"], pound["effect_id"]) == (1, "TOUGH", 3, 5)
        assert {row["effect_id"] for row in value["moves"]} == set(range(1, 24)) - {3}
        assert all("jam" not in row and "previous" not in row for row in value["moves"])


def test_fossils_distinguish_version_and_trainer_parity(assets: Path) -> None:
    for group, value in _catalog(assets)["groups"].items():
        mining = {row["identifier"]: row for row in value["mining"]}
        skull = mining["MINING_TREASURE_SKULL_FOSSIL"]["weights"]
        armor = mining["MINING_TREASURE_ARMOR_FOSSIL"]["weights"]
        assert skull[0] > 0 and skull[1] == 0 and skull[2] > 0 and skull[3] == 0, group
        assert armor[0] == 0 and armor[1] > 0 and armor[2] == 0 and armor[3] > 0, group
        assert mining["MINING_TREASURE_OLD_AMBER"]["weights"][:2] == [0, 0]


def test_tower_series_and_fixed_brains_keep_their_native_configurations(assets: Path) -> None:
    for value in _catalog(assets)["groups"].values():
        battle = value["battles"]
        assert battle["tower_ranges"][0] == {"series": 1, "ordinary": [0, 99], "last": [100, 119]}
        assert battle["tower_ranges"][-1]["ordinary"] == [200, 299]
        sets = {row["id"]: row for row in battle["sets"]}
        assert {sets[i]["species"] for i in battle["trainers"][305]} == {464, 350, 149}
        assert {sets[i]["species"] for i in battle["trainers"][306]} == {485, 488, 486}
    frontier = _catalog(assets)["groups"]["platinum"]["battles"]["frontier"]
    assert frontier["ranges"]["castle"][0]["ordinary"] == [0, 98]
    assert frontier["ranges"]["arcade"][0]["last"] == [100, 118]
    assert frontier["factory"]["level50"][0]["max"] == 150
    assert frontier["factory"]["open_player"][0]["min"] == 351
    assert frontier["factory"]["open_opponent"][0]["min"] == 351
    assert frontier["hall"]["ranks"][0] == [1, 154]
    assert len(frontier["hall"]["sets"]) == 477


@pytest.mark.parametrize("subject", ["goods", "traps"])
def test_missing_underground_entries_are_rejected(assets: Path, subject: str) -> None:
    value = _catalog(assets)["groups"]["platinum"]
    value["underground"][subject].pop()
    with pytest.raises(ValueError, match="incomplet"):
        validate_extras(value, True)


@pytest.mark.parametrize("subject", ["sets", "trainers", "tower_ranges"])
def test_missing_battle_entries_are_rejected(assets: Path, subject: str) -> None:
    value = _catalog(assets)["groups"]["platinum"]
    value["battles"][subject].pop()
    with pytest.raises(ValueError):
        validate_extras(value, True)


def test_frontier_cannot_leak_into_diamond_pearl(assets: Path) -> None:
    value = _catalog(assets)["groups"]["platinum"]
    value["battles"]["trainers"] = value["battles"]["trainers"][:307]
    with pytest.raises(ValueError, match="mauvaise version"):
        validate_extras(value, False)
