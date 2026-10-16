"""Règles sauvages DS sur des sources réduites : lecture des fragments du moteur, remplacements d'emplacements,
combinaisons de conditions, terrains et comparaison avec PokéAPI."""

import pytest

from pokemaps_data.compare_wild_gen4 import _signature
from pokemaps_data.maps_terrain_gen4 import BlockView, _kind, cell_point
from pokemaps_data.pret_gen4_encounter_tables import EncounterTable, WaterSlot
from pokemaps_data.pret_gen4_engine_text import (
    asm_data,
    asm_function,
    asm_threshold_rates,
    c_function,
    c_initializer,
    c_threshold_rates,
)
from pokemaps_data.pret_gen4_land import FX_ONE
from pokemaps_data.pret_gen4_wild import WildContext, _form_note, _walk, _water, honey_note
from pokemaps_data.pret_gen4_wild_extra import MARSH_LOCAL, MARSH_NATIONAL, TROPHY_GARDEN
from pokemaps_data.pret_gen4_wild_rules import (
    HoneyRules,
    Replacements,
    SlotRates,
    TileRules,
    WildRules,
    _value_rates,
)
from pokemaps_data.pret_gen4_wild_rules_dp import _roamer_table
from pokemaps_data.validate_encounters_gen4 import condition_axis, condition_combinations, wrong_combinations

LAND = (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1)
WATER = (60, 30, 5, 4, 1)
ROUTE, SWARM_ROUTE, RADAR_ROUTE, GARDEN, MARSH = 1, 2, 3, 4, 5
GRASS, TALL_GRASS, CAVE, WATER_TILE, DEEP_WATER = 2, 3, 8, 16, 17


def _tiles() -> TileRules:
    flags = [0] * 256
    for value in (GRASS, TALL_GRASS, CAVE):
        flags[value] = 2
    flags[WATER_TILE], flags[DEEP_WATER] = 3, 1
    return TileRules(tuple(flags), GRASS, frozenset({GRASS, TALL_GRASS}))


def _rules() -> WildRules:
    honey = HoneyRules(
        (7,), (("platinum", (2, 3, 4)),), (40, 20, 20, 10, 5, 5), (5, 15), (10, 70, 20, 0), (9, 20, 70, 1), 26
    )
    return WildRules(
        rates=SlotRates(LAND, WATER, (("old-rod", WATER), ("good-rod", WATER), ("super-rod", WATER))),
        replacements=Replacements(swarm=(0, 1), time=(2, 3), radar=(4, 5, 10, 11), daily=(6, 7), dual_slot=(8, 9)),
        tiles=_tiles(),
        swarm_headers=(SWARM_ROUTE,),
        honey=honey,
        trophy_garden=GARDEN,
        great_marsh=(MARSH,),
        feebas=(9, (10, 20)),
        roamer_headers=(ROUTE,),
        roamers=((481, 50),),
        unown_forms=((0, 1), (5,)),
    )


def _context() -> WildContext:
    extra = {TROPHY_GARDEN: (35, 39, 52, 113), MARSH_LOCAL: (194, 194, 195, 451), MARSH_NATIONAL: (451, 452)}
    return WildContext(_rules(), extra, frozenset({RADAR_ROUTE}))


def _table(**changes: object) -> EncounterTable:
    """Table dont l'emplacement i porte l'espèce 100 + i ; remplacements sans effet sauf indication."""
    water = tuple(WaterSlot(10, 20, 129) for _ in range(5))
    values: dict[str, object] = {
        "land_rate": 10,
        "land": tuple((5, 100 + index) for index in range(12)),
        "swarms": (100, 101),
        "day": (102, 103),
        "night": (102, 103),
        "radar": (104, 105, 110, 111),
        "form_rates": (0, 0, 0, 0, 0, 0),
        "gba": tuple((game, (108, 109)) for game in ("ruby", "sapphire", "emerald", "firered", "leafgreen")),
        "surf_rate": 0,
        "surf": water,
        "rods": (("old", 0, water), ("good", 0, water), ("super", 0, water)),
    }
    values.update(changes)
    return EncounterTable(**values)  # type: ignore[arg-type]


def _rows(slots: tuple) -> list[tuple[float, frozenset[str]]]:
    return [(slot.chance, frozenset(slot.conditions)) for slot in slots]


def test_c_fragments_are_read_without_comments() -> None:
    text = """
    // static int Leurre(int roll) { return 0; }
    static int GetSlot(int roll) /* tirage */ {
        if (roll < 60) { return 0; } else if (roll >= 60 && roll < 90) { return 1; }
        if (roll == 95) { return 3; }
        { return roll < 95 ? 2 : 4; }
    }
    static const u16 sTable[] = { 1, /* deux */ 2 };
    """
    body = c_function(text, "GetSlot", "test")
    assert body.count("{") == body.count("}") and "tirage" not in body
    assert c_threshold_rates(body, "roll", 5, "test") == (60, 30, 5, 1, 4)
    assert c_initializer(text, "sTable", "test").split() == ["1,", "2"]
    with pytest.raises(ValueError, match="Absente introuvable"):
        c_function(text, "Absente", "test")
    with pytest.raises(ValueError, match="4 probabilités attendues"):
        c_threshold_rates(body, "roll", 4, "test")


def test_asm_fragments_skip_the_bound_check_and_read_equalities() -> None:
    text = """
    thumb_func_start GetSlot
GetSlot: ; 0x0
    cmp r0, #100 ; GF_AssertFail
    cmp r0, #0x3c
    blt _a
    cmp r0, #0x5a
    cmp r0, #0x5f
    bne _b
    thumb_func_start Next
Next:
    bx lr
Data: ; 0x10
    .byte 1, 2
    .word 0x00000203
"""
    lines = asm_function(text, "GetSlot", "test")
    assert lines[0] == "cmp r0, #100" and "Next:" not in lines
    assert asm_threshold_rates(lines, "r0", 5, "test") == (60, 30, 5, 1, 4)
    assert asm_data(text, "Data", "test") == bytes([1, 2, 3, 2, 0, 0])
    with pytest.raises(ValueError, match="Absente introuvable"):
        asm_function(text, "Absente", "test")


def test_value_rates_follow_the_engine_draw() -> None:
    body = "if (roll < 40) { *slot = 0; } else if (roll < 60) { *slot = 1; } else { *slot = 0; }"
    assert _value_rates(body, "slot", 2, "test") == (80, 20)
    with pytest.raises(ValueError, match="tirage incohérent"):
        _value_rates(body.replace("roll < 60", "roll < 30"), "slot", 2, "test")


def test_rules_reject_impossible_shapes() -> None:
    with pytest.raises(ValueError, match="incohérents"):
        Replacements(swarm=(0, 1), time=(1, 2), radar=(4,), daily=(6,), dual_slot=(8,))
    with pytest.raises(ValueError, match="probabilités sauvages DS invalides"):
        SlotRates(LAND[:11], WATER, (("old-rod", WATER), ("good-rod", WATER), ("super-rod", WATER)))
    with pytest.raises(ValueError, match="comportements de cases"):
        TileRules(_tiles().flags, CAVE, frozenset({GRASS}))


def test_time_of_day_replaces_two_slots_and_morning_keeps_the_base() -> None:
    slots = _walk(ROUTE, _table(day=(200, 103), night=(201, 103)), _context())
    replaced = [slot for slot in slots if slot.conditions]
    assert [(s.species, s.conditions, s.chance) for s in replaced] == [
        (102, ("time-morning",), 10),
        (200, ("time-day",), 10),
        (201, ("time-night",), 10),
    ]
    # Le deuxième emplacement horaire garde la même espèce à toute heure : il reste sans condition.
    assert sum(1 for slot in slots if slot.species == 103) == 1
    assert wrong_combinations(_rows(slots)) == []


def test_swarm_and_radar_only_where_the_engine_allows_them() -> None:
    table = _table(swarms=(300, 301), radar=(302, 303, 304, 305))
    plain = _walk(ROUTE, table, _context())
    assert all(not slot.conditions for slot in plain) and len(plain) == 12
    swarm = _walk(SWARM_ROUTE, table, _context())
    assert {s.species for s in swarm if s.conditions == ("swarm-yes",)} == {300, 301}
    radar = _walk(RADAR_ROUTE, table, _context())
    assert {s.species for s in radar if s.conditions == ("radar-on",)} == {302, 303, 304, 305}
    assert sum(s.chance for s in radar if s.conditions == ("radar-on",)) == 22
    for slots in (plain, swarm, radar):
        assert wrong_combinations(_rows(slots)) == []


def test_dual_slot_has_one_value_per_cartridge() -> None:
    gba = tuple(
        (game, (400 + index, 109)) for index, game in enumerate(("ruby", "sapphire", "emerald", "firered", "leafgreen"))
    )
    slots = _walk(ROUTE, _table(gba=gba), _context())
    assert [s.conditions[0] for s in slots if s.conditions] == [
        "slot2-none",
        "slot2-ruby",
        "slot2-sapphire",
        "slot2-emerald",
        "slot2-firered",
        "slot2-leafgreen",
    ]
    assert wrong_combinations(_rows(slots)) == []


def test_daily_pokemon_are_averaged_and_never_predicted() -> None:
    garden = _walk(GARDEN, _table(), _context())
    daily = [s for s in garden if "backlot-mentioned" in s.conditions]
    assert [s.species for s in daily] == [35, 39, 52, 113, 35, 39, 52, 113]
    assert sum(s.chance for s in daily) == 10
    assert sum(s.chance for s in garden if s.conditions == ("backlot-not-mentioned",)) == 10
    marsh = _walk(MARSH, _table(), _context())
    assert not any(s.species in (106, 107) for s in marsh)
    local = [s for s in marsh if s.conditions == ("story-progress-before-national-dex",)]
    assert sum(s.chance for s in local if s.species == 194) == 5  # deux entrées sur quatre, deux emplacements
    for slots in (garden, marsh):
        assert wrong_combinations(_rows(slots)) == []


def test_water_levels_and_form_notes() -> None:
    water = _water((WaterSlot(20, 10, 422), *(WaterSlot(5, 5, 129) for _ in range(4))), WATER)
    assert (water[0].min_level, water[0].max_level, water[0].chance) == (10, 20, 60)
    table = _table(form_rates=(1, 0, 0, 0, 0, 2))
    assert _form_note({422, 423}, table, _rules()) == "Sancoki Mer Orient. Tritosor Mer Occident."
    assert _form_note({201}, table, _rules()) == "Formes de Zarbi : F."
    assert _form_note({201}, _table(), _rules()) == "Formes de Zarbi : A, B."
    assert "A 70 %, B 20 %, rien 10 %" in honey_note(_rules())


def test_condition_combinations_choose_one_value_per_condition() -> None:
    assert condition_axis("time-day") == condition_axis("time-night") == "time-"
    assert condition_axis("story-progress-national-dex") == "national-dex"
    combinations = condition_combinations([frozenset({"time-day"}), frozenset({"time-night", "radar-on"})])
    assert combinations is not None and len(combinations) == 2
    rows = [(90.0, frozenset()), (10.0, frozenset({"time-day"}))]
    assert wrong_combinations(rows) == []
    assert wrong_combinations([*rows, (10.0, frozenset({"radar-on"}))]) == [(("radar-on", "time-day"), 110.0)]
    many = [frozenset({f"slot2-{n}", f"time-{n}", f"radar-{n}", f"swarm-{n}"}) for n in range(5)]
    assert condition_combinations(many) is None


def test_comparison_ignores_conditions_that_change_nothing() -> None:
    # PokéAPI répète la condition sur un emplacement inchangé ; le moteur l'omet.
    pokeapi = [
        (16, 2, 2, 50.0, frozenset({"time-day"})),
        (16, 2, 2, 50.0, frozenset({"time-night"})),
        (19, 3, 3, 50.0, frozenset()),
    ]
    engine = [(16, 2, 2, 50.0, frozenset()), (19, 3, 3, 50.0, frozenset())]
    for selected in (frozenset({"time-day"}), frozenset({"time-night"})):
        assert _signature(pokeapi, selected) == _signature(engine, selected) == ((16, 2, 2, 50.0), (19, 3, 3, 50.0))
    assert _signature(pokeapi, frozenset()) != _signature(engine, frozenset())


def test_terrain_of_each_tile_behavior() -> None:
    tiles, walk, fishing = _tiles(), frozenset({"walk"}), frozenset({"old-rod"})
    assert _kind(GRASS, False, tiles, walk) == "grass"
    assert _kind(CAVE, False, tiles, walk) == "floor"
    assert _kind(CAVE, True, tiles, walk) is None
    assert _kind(0, False, tiles, walk) is None
    assert _kind(WATER_TILE, False, tiles, frozenset({"surf"})) == "water"
    assert _kind(DEEP_WATER, False, tiles, frozenset({"surf"})) is None
    assert _kind(DEEP_WATER, False, tiles, fishing) == "water"
    assert _kind(WATER_TILE, False, tiles, walk) is None


def test_cell_point_lifts_raised_ground_on_the_oblique_view() -> None:
    view = BlockView(column=1, row=2, altitude=0, cotangent=FX_ONE // 2)
    ground = cell_point((33, 64), 0, view, (512, 1024, 1536, 2048))
    assert ground == (24, 8)
    assert cell_point((33, 64), 32 * FX_ONE, view, (512, 1024, 1536, 2048)) == (24, -8)


def test_dp_roamers_are_read_in_the_assembly() -> None:
    text = "_02060580: .word 0x000001E1\n"
    lines = [
        "cmp r5, #0x0",
        "beq _a",
        "cmp r5, #0x1",
        "beq _b",
        "b _end",
        "_a:",
        "ldr r7, _02060580",
        "mov r6, #0x32",
        "b _end",
        "_b:",
        "mov r7, #0x7a",
        "lsl r7, r7, #0x2",
        "mov r6, #0x28",
        "b _end",
    ]
    assert _roamer_table(text, lines) == {0: (481, 50), 1: (488, 40)}
    with pytest.raises(ValueError, match="errant 0"):
        _roamer_table("", lines)
