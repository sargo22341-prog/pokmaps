"""Règles des outils DS vérifiées dans chacun des deux moteurs épinglés."""

import re
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_engine_text import asm_function, c_function, c_initializer
from pokemaps_data.sources import pret_dir

_CACHE = Path(__file__).resolve().parents[1] / ".cache"


@pytest.mark.pipeline
def test_friendship_engine_order_and_item_order_are_distinct_in_both_games(source_cache_ready: None) -> None:
    sources = (
        ("pokediamond", "arm9/src/pokemon.c", "MonApplyFriendshipMod", "sFriendshipModTable"),
        ("pokeplatinum", "src/pokemon.c", "Pokemon_UpdateFriendship", "sFriendshipChangeTable"),
    )
    expected = [
        (5, 3, 2),
        (5, 3, 2),
        (1, 1, 0),
        (3, 2, 1),
        (1, 1, 0),
        (1, 1, 1),
        (-1, -1, -1),
        (-5, -5, -10),
        (-5, -5, -10),
        (3, 2, 1),
    ]
    for repo, relative, function, table in sources:
        source = (pret_dir(_CACHE, repo) / relative).read_text(encoding="utf-8")
        rows = re.findall(r"\{\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\s*}", c_initializer(source, table, relative))
        assert [tuple(map(int, row)) for row in rows] == expected
        body = c_function(source, function, relative)
        assert body.index("ITEM_LUXURY_BALL") < body.index("MON_DATA_EGG_LOCATION") < body.index("150 / 100")
    source = (pret_dir(_CACHE, "pokeplatinum") / "src/item_use_pokemon.c").read_text(encoding="utf-8")
    body = c_function(source, "UpdatePokemonFriendship", "items")
    assert body.index("HELD_ITEM_FRIENDSHIP_UP_MULTIPLIER") < body.index("ITEM_LUXURY_BALL")
    assert body.index("ITEM_LUXURY_BALL") < body.index("MON_DATA_EGG_LOCATION")
    source = (pret_dir(_CACHE, "pokediamond") / "arm9/src/use_item_on_mon.c").read_text(encoding="utf-8")
    body = c_function(source, "DoItemFriendshipMod", "items-dp")
    assert body.index("150 / 100") < body.index("ITEM_LUXURY_BALL") < body.index("MON_DATA_EGG_LOCATION")


@pytest.mark.pipeline
def test_egg_level_masuda_and_repeated_iv_index_are_present_in_both_engines(source_cache_ready: None) -> None:
    relative = "arm9/overlays/05/asm/ov05_021EC458.s"
    diamond = (pret_dir(_CACHE, "pokediamond") / relative).read_text(encoding="utf-8")
    ivs = asm_function(diamond, "ov05_021EC9D4", relative)
    assert "sub r1, r1, r5" in ivs
    assert "add r1, r5, #0" in ivs and "bl ov05_021EC99C" in ivs
    nature_dp = asm_function(diamond, "ov05_021EC8A8", relative)
    assert nature_dp.index("bl GetBoxMonGender") < nature_dp.index("cmp r0, #0x84") < nature_dp.index("cmp r0, #0xe5")
    assert any("0x00007FFF" in line for line in nature_dp)
    egg = asm_function(diamond, "ov05_Daycare_CreateEgg", relative)
    assert "bl Save_Daycare_MasudaCheck" in egg and "cmp r5, #4" in egg
    assert "mov r2, #1" in egg and "bl CreateMon" in egg
    relative = "src/overlay005/daycare.c"
    platinum = (pret_dir(_CACHE, "pokeplatinum") / relative).read_text(encoding="utf-8")
    ivs_c = c_function(platinum, "Egg_InheritIVs", relative)
    assert "availableIVs[LCRNG_Next() % (STAT_MAX - i)]" in ivs_c
    assert "RemoveIVIndexFromList(availableIVs, i)" in ivs_c
    initial = c_function(platinum, "Egg_SetInitialData", relative)
    assert "Daycare_AreParentLanguagesDifferent" in initial and "i < 4" in initial
    assert "EGG_POKEMON_LEVEL" in initial
    nature = c_function(platinum, "Daycare_GetParentToInheritNature", relative)
    assert nature.index("GENDER_FEMALE") < nature.index("SPECIES_DITTO") < nature.index("ITEM_EVERSTONE")
    assert "0xffff / 2" in nature


@pytest.mark.pipeline
def test_nine_incenses_and_manaphy_are_read_from_the_engine(source_cache_ready: None) -> None:
    source = (pret_dir(_CACHE, "pokeplatinum") / "src/overlay005/daycare.c").read_text(encoding="utf-8")
    triples = re.findall(r"\{ SPECIES_(\w+), ITEM_(\w+_INCENSE), SPECIES_(\w+) }", source)
    assert set(triples) == {
        ("WYNAUT", "LAX_INCENSE", "WOBBUFFET"),
        ("AZURILL", "SEA_INCENSE", "MARILL"),
        ("MIME_JR", "ODD_INCENSE", "MR_MIME"),
        ("BONSLY", "ROCK_INCENSE", "SUDOWOODO"),
        ("MUNCHLAX", "FULL_INCENSE", "SNORLAX"),
        ("MANTYKE", "WAVE_INCENSE", "MANTINE"),
        ("BUDEW", "ROSE_INCENSE", "ROSELIA"),
        ("HAPPINY", "LUCK_INCENSE", "CHANSEY"),
        ("CHINGLING", "PURE_INCENSE", "CHIMECHO"),
    }
    assert "if (eggSpecies == SPECIES_MANAPHY)" in source and "eggSpecies = SPECIES_PHIONE;" in source


@pytest.mark.pipeline
def test_platinum_spa_is_a_random_gain_not_a_friendship_tier(source_cache_ready: None) -> None:
    root = pret_dir(_CACHE, "pokeplatinum")
    source = (root / "res/field/scripts/scripts_resort_area_ribbon_syndicate_2f.s").read_text(encoding="utf-8")
    assert "GoToIfLt VAR_RESULT, 5," in source
    assert "GoToIfLt VAR_RESULT, 30," in source
    assert set(re.findall(r"IncreasePartyMonFriendship (\d+),", source)) == {"5", "10", "30"}
    massage = (root / "res/field/scripts/scripts_veilstone_city_southwest_house.s").read_text(encoding="utf-8")
    assert "IncreasePartyMonFriendship 3," in massage


@pytest.mark.pipeline
def test_sinnoh_roaming_network_has_twenty_nine_entries_and_platinum_birds(source_cache_ready: None) -> None:
    relative = "src/roaming_pokemon.c"
    source = (pret_dir(_CACHE, "pokeplatinum") / relative).read_text(encoding="utf-8")
    routes = c_initializer(source, "RoamingPokemonRoutes", relative)
    assert len(re.findall(r"= MAP_HEADER_", routes)) == 29
    assert "MAP_HEADER_ROUTE_222" in routes and "MAP_HEADER_VALLEY_WINDWORKS_OUTSIDE" in routes
    assert "MAP_HEADER_FUEGO_IRONWORKS_OUTSIDE" in routes
    assert "level = 60;" in source and "level = 50;" in source
    for species in ("MESPRIT", "CRESSELIA", "MOLTRES", "ZAPDOS", "ARTICUNO"):
        assert "species = SPECIES_" + species in source


@pytest.mark.pipeline
def test_service_friendship_uses_bell_before_ball_and_egg_location_in_both_games(source_cache_ready: None) -> None:
    for repo, relative, function in (
        ("pokediamond", "arm9/src/scrcmd_party.c", "ScrCmd_AddPartyMonFriendship"),
        ("pokeplatinum", "src/scrcmd_party.c", "ScrCmd_IncreasePartyMonFriendship"),
    ):
        source = (pret_dir(_CACHE, repo) / relative).read_text(encoding="utf-8")
        body = c_function(source, function, relative)
        assert body.index("150") < body.index("ITEM_LUXURY_BALL") < body.index("MON_DATA_EGG_LOCATION")


@pytest.mark.pipeline
def test_diamond_nine_incense_triples_and_roaming_routes_match_platinum(source_cache_ready: None) -> None:
    import struct

    root = pret_dir(_CACHE, "pokediamond")
    source = (root / "arm9/overlays/05/asm/ov05_021EC458.s").read_text(encoding="utf-8")
    table = source.split("ov05_021F7B12: ;", 1)[1].split(".global ov05_021F7B48", 1)[0]
    data = bytes(
        int(v, 16)
        for line in table.splitlines()
        if line.strip().startswith(".byte")
        for v in re.findall(r"0x([0-9A-Fa-f]{2})", line)
    )
    assert list(struct.iter_unpack("<HHH", data)) == [
        (360, 255, 202),
        (298, 254, 183),
        (439, 314, 122),
        (438, 315, 185),
        (446, 316, 143),
        (458, 317, 226),
        (406, 318, 315),
        (440, 319, 113),
        (433, 320, 358),
    ]
    source = (root / "arm9/asm/unk_020603B0.s").read_text(encoding="utf-8")
    table = source.split("UNK_020F7460: ;", 1)[1].split(".global UNK_020F74D4", 1)[0]
    routes = re.findall(r"\.word MAP_(\w+)", table)
    assert len(routes) == 29
    assert routes[-2:] == ["VALLEY_WINDWORKS_EXTERIOR", "FUEGO_IRONWORKS_EXTERIOR"]
    source = (pret_dir(_CACHE, "pokeplatinum") / "src/roaming_pokemon.c").read_text(encoding="utf-8")
    platinum = c_initializer(source, "RoamingPokemonRoutes", "routes-pt")
    assert {route.replace("EXTERIOR", "OUTSIDE") for route in routes} == set(
        re.findall(r"= MAP_HEADER_(\w+)", platinum)
    )


@pytest.mark.pipeline
def test_diamond_service_scripts_give_the_same_massage_and_spa_amounts(source_cache_ready: None) -> None:
    from pokemaps_data.games import DIAMOND_PEARL
    from pokemaps_data.pret_gen4 import Gen4PretRepo

    repo = Gen4PretRepo(pret_dir(_CACHE, "pokediamond"), DIAMOND_PEARL.pret_versions)
    expected = {"MAP_VEILSTONE_MASSAGE_GIRL_HOUSE": {3}, "MAP_RESORT_AREA_RIBBON_SYNDICATE_2F": {5, 10, 30}}
    for header, amounts in expected.items():
        [selected] = [h for h in repo.headers.values() if h.constant == header]
        steps = tuple(repo.flows[selected.scripts].steps.values())
        if "SYNDICATE" in header:
            randoms = [s for s in steps if s.command == "random"]
            assert any(s.arguments[1] == 100 for s in randoms)
            draw = next(s for s in randoms if s.arguments[1] == 100)
            first_gain = min(s.key for s in steps if s.command == "ScrCmd_AddPartyMonFriendship")
            # VAR_RESULT sert aussi au dialogue : seules les comparaisons après le tirage décrivent ses seuils.
            assert {
                s.arguments[1]
                for s in steps
                if s.command == "compare_value"
                and s.arguments[0] == draw.arguments[0]
                and draw.key < s.key < first_gain
            } == {
                5,
                30,
            }
        assert {s.arguments[0] for s in steps if s.command == "ScrCmd_AddPartyMonFriendship"} == amounts
