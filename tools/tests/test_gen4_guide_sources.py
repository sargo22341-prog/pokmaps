"""Faits éditoriaux des guides DS confrontés séparément aux deux moteurs épinglés."""

import re
from pathlib import Path

import pytest

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_engine_text import asm_function, c_function, c_initializer
from pokemaps_data.pret_gen4_flow import CHECK_FLAG, COMPARE_VALUE, COPY_VAR, SET_FLAG, Step, reachable
from pokemaps_data.pret_gen4_offers import daily_flags
from pokemaps_data.sources import PRET_COMMITS, pret_dir

_ROOT = Path(__file__).resolve().parents[2]
_CACHE = _ROOT / "tools/.cache"


@pytest.fixture(scope="module", params=[DIAMOND_PEARL, PLATINUM], ids=["dp", "pt"])
def guide_repo(request: pytest.FixtureRequest, source_cache_ready: None) -> Gen4PretRepo:
    game = request.param
    return Gen4PretRepo(pret_dir(_CACHE, game.pret_repo), game.pret_versions)


def _steps(repo: Gen4PretRepo, header: str) -> tuple[Step, ...]:
    [selected] = [h for h in repo.headers.values() if h.constant == header]
    flow = repo.flows[selected.scripts]
    visited = set().union(*(reachable(flow, entry) for entry in flow.entries))
    return tuple(flow.steps[key] for key in visited)


def _days(steps: tuple[Step, ...]) -> set[int]:
    variables = {s.arguments[-1] for s in steps if "GetDayOfWeek" in s.source}
    # Le marché copie le résultat dans VAR_0x8008 avant ses sept branches.
    for _ in range(3):
        variables |= {s.arguments[0] for s in steps if s.command == COPY_VAR and s.arguments[1] in variables}
    return {
        int(s.arguments[1])
        for s in steps
        if s.command == COMPARE_VALUE and s.arguments[0] in variables and s.arguments[1] in range(7)
    }


def test_friday_and_weekend_use_reachable_scripts_of_each_game(guide_repo: Gen4PretRepo) -> None:
    prefix = "MAP_HEADER_" if guide_repo.platinum else "MAP_"
    windworks = "VALLEY_WINDWORKS_OUTSIDE" if guide_repo.platinum else "VALLEY_WINDWORKS_EXTERIOR"
    assert _days(_steps(guide_repo, prefix + windworks)) == {5}
    weekend = "SURVIVAL_AREA" if guide_repo.platinum else "FIGHT_AREA"
    assert {0, 6} <= _days(_steps(guide_repo, prefix + weekend))
    assert _days(_steps(guide_repo, prefix + "SUNYSHORE_MARKET")) == set(range(7))


def test_clock_periods_are_read_independently_in_both_engines(guide_repo: Gen4PretRepo) -> None:
    relative = "src/rtc.c" if guide_repo.platinum else "arm9/src/gf_rtc.c"
    source = (guide_repo.root / relative).read_text(encoding="utf-8")
    name = "lookup" if guide_repo.platinum else "sTimeOfDayByHour"
    periods = re.findall(r"(?:RTC_)?TIMEOFDAY_(\w+)", c_initializer(source, name, relative))
    expected = ["LATE_NIGHT"] * 4 + ["MORNING"] * 6 + ["DAY"] * 7 + ["TWILIGHT"] * 3 + ["NIGHT"] * 4
    if not guide_repo.platinum:
        translate = {"LATE": "LATE_NIGHT", "MORN": "MORNING", "EVE": "TWILIGHT", "NITE": "NIGHT", "DAY": "DAY"}
        periods = [translate[value] for value in periods]
    assert periods == expected


def test_daily_activities_check_and_set_flags_reset_by_their_own_engine(guide_repo: Gen4PretRepo) -> None:
    platinum = (
        "JUBILIFE_TV_1F",
        "FLOWER_SHOP",
        "PASTORIA_CITY_SOUTHWEST_HOUSE",
        "VEILSTONE_CITY_SOUTHWEST_HOUSE",
        "ROUTE_208_HOUSE",
    )
    diamond = (
        "JUBLIFE_TV_1F",
        "FLOAROMA_FLOWER_SHOP",
        "PASTORIA_SOUTHWEST_HOUSE",
        "VEILSTONE_MASSAGE_GIRL_HOUSE",
        "ROUTE_208_BERRY_MASTER_HOUSE",
    )
    prefix = "MAP_HEADER_" if guide_repo.platinum else "MAP_"
    daily = daily_flags(guide_repo)
    for header in platinum if guide_repo.platinum else diamond:
        steps = _steps(guide_repo, prefix + header)
        checked = {s.arguments[0] for s in steps if s.command == CHECK_FLAG}
        marked = {s.arguments[0] for s in steps if s.command == SET_FLAG}
        assert checked.intersection(marked).intersection(daily), header


def test_pokedex_unlock_counts_seen_species_not_captures(guide_repo: Gen4PretRepo) -> None:
    relative = "src/pokedex.c" if guide_repo.platinum else "arm9/src/pokedex.c"
    source = (guide_repo.root / relative).read_text(encoding="utf-8")
    if guide_repo.platinum:
        body = c_function(source, "Pokedex_LocalDexCompleted", relative)
        assert "Pokedex_NumSeen_Local" in body and "LOCAL_DEX_GOAL" in body
        assert "sExcludedMonsLocal[] = {};" in source
        header = (guide_repo.root / "include/pokedex.h").read_text(encoding="utf-8")
        assert "(REGIONAL_DEX_COUNT - NUM_EXCLUDED_LOCAL)" in header
    else:
        body = c_function(source, "Pokedex_SinnohDexIsComplete", relative)
        assert "Pokedex_CountSinnohDexSeen_OmitMythicals(pokedex) >= 150" in body
        omitted = c_function(source, "Pokedex_CountSinnohDexSeen_OmitMythicals", relative)
        assert "Pokedex_SpeciesIsNotSinnohMythical" in omitted
        mythical = c_function(source, "Pokedex_SpeciesIsNotSinnohMythical", relative)
        assert "SPECIES_MANAPHY" in mythical


def test_platinum_fossils_are_exclusive_by_trainer_id_but_old_fossils_are_renewable(
    source_cache_ready: None,
) -> None:
    path = pret_dir(_CACHE, "pokeplatinum") / "src/underground/mining.c"
    source = path.read_text(encoding="utf-8")
    for name, weights in {"SKULL": (25, 0, 12, 0), "ARMOR": (0, 25, 0, 12)}.items():
        [row] = [line for line in source.splitlines() if f".itemID = MINING_TREASURE_{name}_FOSSIL," in line]
        assert tuple(map(int, re.findall(r"(?:odd|even)TID(?:NatDex)?Weight = (\d+)", row))) == weights
    for name in ("HELIX_FOSSIL", "DOME_FOSSIL", "ROOT_FOSSIL", "CLAW_FOSSIL", "OLD_AMBER"):
        rows = [line for line in source.splitlines() if f".itemID = MINING_TREASURE_{name}," in line]
        assert rows
        assert all(".oddTIDWeight = 0, .evenTIDWeight = 0," in row for row in rows)
        assert all(all(int(n) > 0 for n in re.findall(r"TIDNatDexWeight = (\d+)", row)) for row in rows)
    assert "TrainerInfo_ID(SaveData_GetTrainerInfo(saveData)) % 2" in source


def test_bugs_described_in_guides_are_present_in_the_pinned_engines(source_cache_ready: None) -> None:
    diamond = pret_dir(_CACHE, "pokediamond")
    relative = "arm9/src/gf_rtc.c"
    body = c_function((diamond / relative).read_text(encoding="utf-8"), "GF_RTC_TimeDelta", relative)
    assert "first < last" in body and "return last + (MAX_SECONDS - first);" in body
    platinum = pret_dir(_CACHE, "pokeplatinum")
    fishing = (platinum / "src/overlay006/wild_encounters.c").read_text(encoding="utf-8")
    assert "newEncRate * 2;" in fishing
    pursuit = (platinum / "res/battle/scripts/subscripts/subscript_pursuit.s").read_text(encoding="utf-8")
    assert "UpdateVarFromVar OPCODE_SUB_TO_ZERO, BTLVAR_FIELD_CONDITIONS, BTLVAR_SCRIPT_TEMP" in pursuit


def test_honey_wait_and_expiry_are_six_and_twenty_four_hours_in_both_engines(source_cache_ready: None) -> None:
    relative = "arm9/overlays/05/asm/ov05_021F4CF8.s"
    diamond = (pret_dir(_CACHE, "pokediamond") / relative).read_text(encoding="utf-8")
    ready = asm_function(diamond, "ov05_021F5120", relative)
    assert "cmp r0, #0" in ready and "ble _021F512E" in ready
    assert "_021F5134: .word 0x00000438" in ready  # 18 heures restantes, donc 6 heures écoulées.
    assert "mov r0, #0x5a\n\tlsl r0, r0, #4\n\tstr r0, [r4]" in diamond  # 1 440 minutes.
    relative = "src/overlay005/honey_tree.c"
    platinum = (pret_dir(_CACHE, "pokeplatinum") / relative).read_text(encoding="utf-8")
    ready_c = c_function(platinum, "SixHoursSinceSlathered", relative)
    assert "0 < minutesLeft" in ready_c and "minutesLeft <= (18 * 60)" in ready_c
    slather = c_function(platinum, "HoneyTree_SlatherTree", relative)
    assert "tree->minutesRemaining = (24 * 60)" in slather


def test_guide_sources_name_existing_files_at_the_pinned_commits(source_cache_ready: None) -> None:
    path = _ROOT / "app/src/main/java/org/opensources/pokmaps/data/guide/GuideDefinitions.kt"
    source = path.read_text(encoding="utf-8")
    for repo, prefix in (("pokediamond", "DIAMOND"), ("pokeplatinum", "PLATINUM")):
        assert PRET_COMMITS[repo] in source
        match = re.search(rf"private val {prefix}_GUIDE_SOURCES = listOf\((.*?)\)\.map", source, re.DOTALL)
        assert match is not None
        for relative in re.findall(r'"([^"]+)"', match.group(1)):
            assert (pret_dir(_CACHE, repo) / relative).is_file(), relative
