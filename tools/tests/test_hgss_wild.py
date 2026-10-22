"""Distributions HGSS : alternatives exclusives et ordre des remplacements, sans sources externes."""

import pytest

from pokemaps_data.encounters_hgss import (
    Configuration,
    Distribution,
    Period,
    Radio,
    Slot,
    configurations,
    filter_distributions,
    signature,
)
from pokemaps_data.pret_hgss_wild import distribution, variant
from pokemaps_data.preview_wild_hgss import validate_comparison


def _data() -> dict:
    water = {"rate": 15, "mons": [{"species": "BASE", "level": {"min": 10, "max": 20}} for _ in range(5)]}
    return {
        "land": {
            "rate": 25,
            "mons": [
                {"species": dict.fromkeys(("morn", "day", "nite"), "BASE"), "level": {"HEARTGOLD": 2, "SOULSILVER": 4}}
                for _ in range(12)
            ],
        },
        "surf": water,
        "fishing": dict.fromkeys(("old_rod", "good_rod", "super_rod"), water),
        "rock_smash": {"rate": 20, "mons": water["mons"][:2]},
        "hoenn": ["HOENN_A", "HOENN_B"],
        "sinnoh": ["SINNOH", "SINNOH"],
        "landSwarm": "SWARM",
        "surfSwarm": "SWARM",
        "fishSwarm": "SWARM",
        "nightFish": "NIGHT",
    }


def _species() -> dict[str, int]:
    return {"BASE": 1, "HOENN_A": 2, "HOENN_B": 3, "SINNOH": 4, "SWARM": 5, "NIGHT": 6}


@pytest.mark.parametrize("config", configurations())
def test_every_compatible_configuration_stays_normalized(config: Configuration) -> None:
    for method in ("walk", "surf", "old-rod", "good-rod", "super-rod", "rock-smash"):
        table = distribution(_data(), 0, method, "heartgold", config, _species(), 0)
        assert table is not None
        assert sum(s.chance for s in table.slots) == 100
        assert table.rate == (25 if method == "walk" else 20 if method == "rock-smash" else 15)


def test_swarm_and_radio_replace_disjoint_land_slots_and_keep_version_levels() -> None:
    config = Configuration(Period.NIGHT, Radio.HOENN, True, True, 2)
    table = distribution(_data(), 0, "walk", "soulsilver", config, _species(), 0)
    assert table is not None
    assert [s.species for s in table.slots] == [5, 5, 2, 2, 3, 3, 1, 1, 1, 1, 1, 1]
    assert {s.minimum for s in table.slots} == {4}
    assert signature(table.slots) == ((1, 4, 4, 20), (2, 4, 4, 20), (3, 4, 4, 20), (5, 4, 4, 40))


@pytest.mark.parametrize("method,night,swarm", [("old-rod", 0, 15), ("good-rod", 10, 65), ("super-rod", 30, 100)])
def test_fishing_swarm_overrides_night_replacement(method: str, night: int, swarm: int) -> None:
    for active in (False, True):
        config = Configuration(Period.NIGHT, swarm=active, national=True)
        table = distribution(_data(), 0, method, "heartgold", config, _species(), 2)
        assert table is not None
        assert sum(s.chance for s in table.slots if s.species == 6) == (0 if active else night)
        assert sum(s.chance for s in table.slots if s.species == 5) == (swarm if active else 0)


def test_swarm_only_applies_to_eligible_method_and_location() -> None:
    config = Configuration(swarm=True, national=True)
    for eligible, chance in ((None, 0), (0, 0), (1, 60), (2, 0)):
        table = distribution(_data(), 0, "surf", "heartgold", config, _species(), eligible)
        assert table is not None
        assert sum(s.chance for s in table.slots if s.species == 5) == chance


@pytest.mark.parametrize("radio,day", [(Radio.HOENN, 2), (Radio.SINNOH, 3)])
def test_radio_requires_its_weekday_and_national_dex(radio: Radio, day: int) -> None:
    with pytest.raises(ValueError, match="incompatible"):
        Configuration(radio=radio, weekday=day)
    with pytest.raises(ValueError, match="incompatible"):
        Configuration(radio=radio, national=True, weekday=(day + 1) % 7)
    with pytest.raises(ValueError, match="radio"):
        Configuration(radio="hoenn+sinnoh", national=True, weekday=day)
    with pytest.raises(ValueError, match="essaim"):
        Configuration(swarm=True)


def test_filters_ignore_metadata_without_effect_and_keep_tree_alternatives_separate() -> None:
    slots = (Slot(1, 2, 4, 100),)
    common = Distribution("heartgold", 1, "headbutt-common", Configuration(), None, slots)
    rare = Distribution("heartgold", 1, "headbutt-rare", Configuration(), None, slots)
    walking = Distribution("heartgold", 1, "walk", Configuration(), 20, slots)
    selection = Configuration(national=True, weekday=4)
    assert filter_distributions((common, rare, walking), "heartgold", "headbutt-common", selection) == (common,)
    assert filter_distributions((walking,), "heartgold", "walk", selection) == (walking,)
    with pytest.raises(ValueError, match="filtre"):
        filter_distributions((walking,), "heartgold", "honey-tree", selection)


def test_invalid_native_values_fail_with_named_errors() -> None:
    with pytest.raises(ValueError, match="variante"):
        variant({"platinum": 4}, "heartgold")
    with pytest.raises(ValueError, match="emplacement"):
        Slot(494, 2, 4, 100)
    with pytest.raises(ValueError, match="100 %"):
        Distribution("heartgold", 1, "walk", Configuration(), 20, (Slot(1, 2, 4, 90),))
    data = _data()
    data["land"]["mons"] = []
    with pytest.raises(ValueError, match="emplacements"):
        distribution(data, 0, "walk", "heartgold", Configuration(), _species(), None)


def test_comparison_rejects_unknown_difference_instead_of_hiding_it() -> None:
    row = {
        "method": "rock-smash",
        "category": "probabilites",
        "pokeapi": [(74, 3, 6, 10), (74, 8, 14, 90)],
        "engine": [(74, 3, 6, 20), (74, 8, 14, 80)],
    }
    validate_comparison({"differences": [row]})
    with pytest.raises(ValueError, match="inexpliqué"):
        validate_comparison({"differences": [row | {"method": "walk"}]})
    with pytest.raises(ValueError, match="non reconnu"):
        validate_comparison({"differences": [row | {"engine": [(74, 3, 6, 100)]}]})
