"""Comparaison des contenus livrés avec chaque désassemblage DS épinglé."""

import json
import re
import struct
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_engine_text import asm_data, asm_function, c_function, c_initializer
from pokemaps_data.pret_gen4_source import metang_enum
from pokemaps_data.pret_sinnoh_battle import battle_catalog
from pokemaps_data.pret_sinnoh_content import berries, contest_appeals, contests
from pokemaps_data.pret_sinnoh_frontier import frontier_catalog
from pokemaps_data.pret_sinnoh_mining import mining_catalog
from pokemaps_data.pret_sinnoh_underground import underground_catalog
from pokemaps_data.sinnoh_catalog import build_sinnoh_catalog
from pokemaps_data.sources import pret_dir

_CACHE = Path(__file__).resolve().parents[1] / ".cache"


@pytest.mark.pipeline
@pytest.mark.parametrize("group,repo", [("diamond-pearl", "pokediamond"), ("platinum", "pokeplatinum")])
def test_every_content_row_matches_its_own_engine(
    assets: Path, source_cache_ready: None, group: str, repo: str
) -> None:
    root = pret_dir(_CACHE, repo)
    platinum = pret_dir(_CACHE, "pokeplatinum")
    value = json.loads((assets / "sinnoh.json").read_text(encoding="utf-8"))["groups"][group]
    rows = berries(root, group == "platinum")
    assert {row["identifier"]: row for row in rows} == {
        row["identifier"]: {key: number for key, number in row.items() if key != "name"} for row in value["berries"]
    }
    effects = metang_enum(platinum / "generated/move_contest_effects.txt")
    appeals = contest_appeals(root)
    assert all(row["appeal"] == appeals[row["effect_id"]] for row in value["moves"])
    assert contests(root, group == "platinum", effects) == [
        {key: row[key] for key in ("id", "category", "effect_id")} for row in value["moves"]
    ]
    underground = underground_catalog(root, platinum, group == "platinum")
    assert underground == {
        key: [{k: v for k, v in row.items() if k != "name"} for row in rows]
        for key, rows in value["underground"].items()
    }
    mining = mining_catalog(root, platinum, "platinum" if group == "platinum" else "diamond")
    assert mining == [{key: row[key] for key in ("id", "identifier", "weights")} for row in value["mining"]]
    battle = battle_catalog(root, group == "platinum")
    assert battle["trainers"] == value["battles"]["trainers"]
    assert battle["tower_ranges"] == value["battles"]["tower_ranges"]
    assert battle["sets"] == [{key: row[key] for key in battle["sets"][0]} for row in value["battles"]["sets"]]


@pytest.mark.pipeline
def test_platinum_frontier_and_hall_match_the_engine(assets: Path, source_cache_ready: None) -> None:
    value = json.loads((assets / "sinnoh.json").read_text(encoding="utf-8"))["groups"]["platinum"]["battles"][
        "frontier"
    ]
    source = frontier_catalog(pret_dir(_CACHE, "pokeplatinum"))
    assert source["ranges"] == value["ranges"]
    assert source["factory"] == value["factory"]
    assert source["hall"]["ranks"] == value["hall"]["ranks"]
    assert source["hall"]["sets"] == [
        {key: row[key] for key in source["hall"]["sets"][0]} for row in value["hall"]["sets"]
    ]


@pytest.mark.pipeline
def test_content_generation_is_byte_reproducible(assets: Path, tmp_path: Path, source_cache_ready: None) -> None:
    build_sinnoh_catalog(_CACHE, tmp_path)
    assert (tmp_path / "sinnoh.json").read_bytes() == (assets / "sinnoh.json").read_bytes()


@pytest.mark.pipeline
def test_mulch_growth_and_drying_rules_are_confirmed_in_both_engines(source_cache_ready: None) -> None:
    platinum = (pret_dir(_CACHE, "pokeplatinum") / "src/berry_patches.c").read_text(encoding="utf-8")
    growth = c_function(platinum, "CalcMinutesRemainingInStage", "baies Platine")
    assert "stageDuration * 60" in growth
    assert "(minutesRemaining * 3) / 4" in growth
    assert "minutesRemaining + (minutesRemaining / 2)" in growth
    drain = c_function(platinum, "CalcMoistureDrainRate", "baies Platine")
    assert "drainRate / 2" in drain and "drainRate + drainRate / 2" in drain
    assert "#define MAX_YIELD_RATING       5" in platinum
    assert "#define MAX_MOISTURE_RATING    100" in platinum
    diamond = (pret_dir(_CACHE, "pokediamond") / "arm9/asm/unk_020250A4.s").read_text(encoding="utf-8")
    growth_dp = asm_function(diamond, "sub_020251B0", "baies Diamant/Perle")
    assert "mov r0, #0x3c" in growth_dp
    assert "lsl r1, r0, #0x1" in growth_dp and "asr r0, r0, #0x2" in growth_dp
    drain_dp = asm_function(diamond, "sub_020251DC", "baies Diamant/Perle")
    assert "asr r0, r1, #0x1" in drain_dp and "add r0, r0, r1" in drain_dp
    plant = asm_function(diamond, "sub_02025274", "plantation Diamant/Perle")
    assert "mov r0, #0x64" in plant and "mov r0, #0x5" in plant
    stable = asm_function(diamond, "sub_02025200", "Fertistable")
    assert "mov r0, #0x6" in stable and "mov r0, #0x4" in stable
    gooey = asm_function(diamond, "sub_02025210", "Fertiglu")
    assert "mov r0, #0xf" in gooey and "mov r0, #0xa" in gooey


@pytest.mark.pipeline
def test_mining_treasure_identifiers_refer_to_the_same_items_in_both_engines(source_cache_ready: None) -> None:
    platinum = pret_dir(_CACHE, "pokeplatinum")
    text = (platinum / "src/underground.c").read_text(encoding="utf-8")
    items = metang_enum(platinum / "generated/items.txt")
    table = c_initializer(text, "sMiningItems", "objets souterrains Platine")
    rows = [(int(number), items[name]) for number, name in re.findall(r"\[(\d+)\] = (ITEM_\w+)", table)]
    assert [number for number, _ in rows] == list(range(49))
    diamond = (pret_dir(_CACHE, "pokediamond") / "arm9/asm/unk_02025954.s").read_text(encoding="utf-8")
    data = asm_data(diamond, "UNK_02105C74", "objets souterrains Diamant/Perle")
    assert len(data) == 100 and data[-2:] == b"\0\0"
    assert list(struct.unpack("<49H", data[:98])) == [item for _, item in rows]
