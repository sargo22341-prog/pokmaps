"""Réserves prouvées communes, différences HGSS et consultation des archives sans réseau."""

import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest

from pokemaps_data.achievement_resources import build_achievement_resources, hgss_achievements
from pokemaps_data.compare_frontier_hgss import _equal
from pokemaps_data.preview_content_hgss import CONTRACT, read_content
from pokemaps_data.review_combat_hgss import combat_review
from pokemaps_data.validate_combat_hgss import validate_achievements, validate_battles


def _content() -> dict:
    return read_content(CONTRACT.with_name("contenus-hgss-catalogue.json"))


def test_all_five_facilities_and_native_reserves_are_available_offline() -> None:
    data = _content()
    battles = data["battles"]
    validate_battles(battles)
    assert len(battles["sets"]) == 950
    assert len(battles["trainers"]) == 315
    assert len(battles["frontier"]["hall"]["sets"]) == 477
    assert battles["tower_ranges"][0]["ordinary"] == [0, 99]
    assert battles["frontier"]["ranges"]["factory"][0]["ordinary"] == [0, 98]
    assert battles["frontier"]["hall"]["ranks"][-1] == [271, 477]
    html = "\n".join(combat_review(data))
    assert all(f'id="set-{i}"' in html for i in range(1, 951))
    assert all(f'id="hall-{i}"' in html for i in range(1, 478))
    assert all(f'id="ra-{r["identifier"]}"' in html for r in data["achievements"]["entries"])
    assert "<script" not in html and "https://" not in html


def test_factory_preserves_hgss_champion_differences_instead_of_copying_platinum() -> None:
    factory = _content()["battles"]["frontier"]["factory"]
    assert (factory["level50"][9]["min"], factory["level50"][9]["max"]) == (759, 950)
    assert (factory["open_opponent"][8]["min"], factory["open_opponent"][8]["max"]) == (351, 486)
    assert factory["open_player"][8] == factory["open_opponent"][8]
    assert factory["level50"][8]["ivs"] == 12
    with pytest.raises(ValueError, match="import refusé"):
        _equal(factory["level50"][9], factory["level50"][8], "Cardus")


def test_rewards_preserve_costs_and_do_not_confuse_bag_check_with_delivered_quantity() -> None:
    rewards = _content()["battles"]["rewards"]
    assert rewards["tower"]["boss"] == 20
    assert rewards["tower"]["tables"]["link"] == [0, 8, 9, 11, 12, 14, 15, 18]
    offers = rewards["exchange"]["offers"]
    assert len(offers) == 42
    pp_up = next(r for r in offers if r["label"] == "_0618")
    assert pp_up["item"] == 50 and pp_up["cost"] == 48
    assert pp_up["quantity"] == 1 and pp_up["required_bag_space"] == 48


@pytest.mark.parametrize("defect", ["set", "trainer", "factory", "photo"])
def test_corrupt_battle_data_is_rejected(defect: str) -> None:
    battles = deepcopy(_content()["battles"])
    if defect == "set":
        battles["sets"][0]["moves"][0] = 0
    elif defect == "trainer":
        battles["trainers"][0].append(0)
    elif defect == "factory":
        battles["frontier"]["factory"]["level50"][9]["min"] = 351
    elif defect == "photo":
        battles["facilities"][2]["gold"] = 49
    with pytest.raises(ValueError, match="HGSS"):
        validate_battles(battles)


def test_shared_set_has_all_ids_points_missables_and_version_specific_thresholds() -> None:
    data = hgss_achievements()
    validate_achievements(_content()["achievements"])
    assert data["versions"] == [15, 16] and data["game_id"] == 7212
    assert len(data["entries"]) == len({r["identifier"] for r in data["entries"]}) == 136
    entries = {r["identifier"]: r for r in data["entries"]}
    assert entries[119420]["missable"] and "13" in entries[119420]["description"]
    assert "373" in entries[123898]["description"] and "371" in entries[123898]["description"]
    assert "Master Ball" in entries[125540]["description"]
    assert "externe" in entries[123534]["description"]
    broken = deepcopy(data)
    broken["entries"].pop()
    with pytest.raises(ValueError, match="ensemble partagé"):
        validate_achievements(broken)


def test_generated_resources_define_shared_achievement_ids_only_once(tmp_path: Path) -> None:
    build_achievement_resources(tmp_path)
    shared = ET.parse(tmp_path / "strings_achievements_15.xml").getroot()
    alias = ET.parse(tmp_path / "strings_achievements_16.xml").getroot()
    assert len(shared.findall("array")) == 137
    assert [r.text for r in alias.find("array")] == [r.text for r in shared.find("array[@name='achievements_15']")]
    names = [node.attrib["name"] for p in tmp_path.glob("*.xml") for node in ET.parse(p).getroot()]
    assert len(names) == len(set(names))
