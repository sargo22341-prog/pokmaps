"""Contrôle des règles de capture communes aux moteurs DS épinglés, sans réseau."""

import csv
import re
from pathlib import Path

from pokemaps_data.pret_gen4_engine_text import asm_data, asm_function, c_function, c_initializer
from pokemaps_data.sources import POKEAPI_COMMIT, pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"
DP_SCRIPT = "arm9/overlays/11/asm/ov11_02232264.s"
PT_SCRIPT = "src/battle/battle_script.c"


def test_safari_factors_are_identical_in_both_engines(source_cache_ready: None) -> None:
    platinum = (pret_dir(CACHE, "pokeplatinum") / PT_SCRIPT).read_text(encoding="utf-8")
    diamond = (pret_dir(CACHE, "pokediamond") / DP_SCRIPT).read_text(encoding="utf-8")
    values = tuple(int(value) for value in re.findall(r"\d+", c_initializer(platinum, "sSafariCatchRate", PT_SCRIPT)))
    assert values == tuple(asm_data(diamond, "ov11_0225DCF0", DP_SCRIPT))
    assert values == (
        10,
        40,
        10,
        35,
        10,
        30,
        10,
        25,
        10,
        20,
        10,
        15,
        10,
        10,
        15,
        10,
        20,
        10,
        25,
        10,
        30,
        10,
        35,
        10,
        40,
        10,
    )


def test_dusk_quick_and_water_bonuses_agree(source_cache_ready: None) -> None:
    platinum = (pret_dir(CACHE, "pokeplatinum") / PT_SCRIPT).read_text(encoding="utf-8")
    diamond = (pret_dir(CACHE, "pokediamond") / DP_SCRIPT).read_text(encoding="utf-8")
    c_body = c_function(platinum, "BattleScript_CalcCatchShakes", PT_SCRIPT)
    asm = "\n".join(asm_function(diamond, "CalcBallShakesOnMonCatch", DP_SCRIPT))
    assert "battleCtx->totalTurns < 1" in c_body and "ballMod = 40;" in c_body
    assert "cmp r0, #1\nbge _0223C12E\nmov r5, #0x28" in asm
    assert "TIMEOFDAY_NIGHT" in c_body and "TIMEOFDAY_LATE_NIGHT" in c_body and "TERRAIN_CAVE" in c_body
    assert "cmp r0, #3\nbeq _0223C118" in asm and "cmp r0, #4\nbeq _0223C118" in asm
    assert "cmp r0, #5\nbne _0223C12E\n_0223C118:\nmov r5, #0x23" in asm
    assert "BattleSystem_GetTerrain(battleSys) == TERRAIN_WATER" in c_body
    assert "cmp r0, #7\nbne _0223C12E\nmov r5, #0x23" in asm
    assert "(0xFF << 16) / catchRate" in c_body and "(0xFFFF << 4) / catchRate" in c_body
    assert "mov r0, #0xff\nlsl r0, r0, #0x10" in asm and "0x000FFFF0" in asm


def test_sinnoh_version_ids_match_pinned_pokeapi(source_cache_ready: None) -> None:
    source = CACHE / f"pokeapi-{POKEAPI_COMMIT[:12]}" / "versions.csv"
    with source.open(encoding="utf-8", newline="") as stream:
        rows = {row["identifier"]: (int(row["id"]), int(row["version_group_id"])) for row in csv.DictReader(stream)}
    assert {name: rows[name] for name in ("diamond", "pearl", "platinum")} == {
        "diamond": (12, 8),
        "pearl": (13, 8),
        "platinum": (14, 9),
    }
