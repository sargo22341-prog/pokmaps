"""Conditions du concours, seuils Safari et exclusions des obtentions, sans réseau."""

from dataclasses import replace

import pytest

from pokemaps_data.special_wild_hgss import SafariConfiguration, contest_slots, safari_slots


def _config(days: int, blocks: tuple[int, int, int, int]) -> SafariConfiguration:
    return SafariConfiguration(days, blocks, national=True, objects_unlocked=True)


def _table(bonuses: list[dict]) -> dict:
    return {"mons": {"day": [{"species": "base", "level": 15}] * 10}, "bonus_mons": bonuses}


def _bonus(kind: str, count: int, species: str = "bonus") -> dict:
    return {
        "day": {"species": species, "level": 40},
        "conditions": [{"object_type": "SAFARI_ZONE_OBJECT_TYPE_" + kind, "count": count}],
    }


@pytest.mark.parametrize(
    "days,expected",
    [
        (0, (1, 1, 1, 1)),
        (10, (2, 1, 1, 1)),
        (50, (3, 2, 2, 2)),
        (100, (4, 3, 3, 3)),
        (249, (6, 6, 6, 6)),
        (250, (7, 7, 7, 7)),
        (255, (7, 7, 7, 7)),
    ],
)
def test_maturation_uses_recorded_area_age_and_native_decades(days: int, expected: tuple[int, ...]) -> None:
    assert _config(days, (1, 1, 1, 1)).points == expected


@pytest.mark.parametrize(
    "config",
    [
        {"days": -1},
        {"days": 256},
        {"days": True},
        {"blocks": (31, 0, 0, 0)},
        {"blocks": (10, 10, 10, 1)},
        {"blocks": (1, 0, 0, 0)},
        {"decorative": 31},
        {"blocks": [0, 0, 0, 0]},
    ],
)
def test_safari_rejects_impossible_configurations(config: dict) -> None:
    with pytest.raises(ValueError, match="Safari"):
        SafariConfiguration(**config)


def test_safari_requires_both_thresholds_and_preserves_native_priority() -> None:
    first = _bonus("PLAINS", 2)
    first["conditions"].append({"object_type": "SAFARI_ZONE_OBJECT_TYPE_FOREST", "count": 2})
    table = _table([first, _bonus("WATER", 1, "other")])
    species = {"base": 19, "bonus": 25, "other": 129}
    slots = safari_slots(table, "day", _config(0, (2, 1, 0, 1)), species)
    assert [s.species for s in slots] == [129] + [19] * 9
    slots = safari_slots(table, "day", _config(0, (2, 2, 0, 1)), species)
    assert [s.species for s in slots] == [25, 129] + [19] * 8
    assert sum(s.chance for s in slots) == 100


def test_safari_caps_replacements_at_ten_and_counts_decorations() -> None:
    table = _table([_bonus("PLAINS", 1)] * 11)
    slots = safari_slots(table, "day", _config(0, (1, 0, 0, 0)), {"base": 19, "bonus": 25})
    assert len(slots) == 10 and all(s.species == 25 for s in slots)
    config = replace(_config(0, (1, 0, 0, 0)), decorative=29)
    assert config.points == (1, 0, 0, 0)
    with pytest.raises(ValueError, match="trente"):
        replace(config, decorative=30)


def test_contest_selects_four_native_sets_without_combining_days() -> None:
    rates = (80, 60, 50, 40, 30, 20, 15, 10, 5, 0)
    rows = [
        {"species": str(group), "lvlmin": "7", "lvlmax": "18", "rate": str(rate)}
        for group in range(4)
        for rate in rates
    ]
    species = {str(i): i + 1 for i in range(4)}
    for day, group in ((1, 1), (3, 2), (5, 3)):
        assert {s.species for s in contest_slots(rows, day, True, species)} == {group + 1}
        assert {s.species for s in contest_slots(rows, day, False, species)} == {1}
    assert sum(s.chance for s in contest_slots(rows, 1, True, species)) == 100
    with pytest.raises(ValueError, match="mardi"):
        contest_slots(rows, 0, False, species)
    rows[-1]["rate"] = "1"
    with pytest.raises(ValueError, match="seuils"):
        contest_slots(rows, 5, True, species)
