"""Régressions des flux et coûts HGSS, sans cache ni réseau."""

import pytest

from pokemaps_data.calendar_hgss import gym_appointment_allowed
from pokemaps_data.offer_rules_hgss import moomoo_seal_quantities, resolve_quantity_rules
from pokemaps_data.pret_gen4_flow import ScriptFlow, Step
from pokemaps_data.pret_gen4_flow_values import values_at
from pokemaps_data.pret_hgss_battles import resolved_battles
from pokemaps_data.pret_hgss_flow import hgss_flow
from pokemaps_data.pret_hgss_flow_context import FlowContext
from pokemaps_data.pret_hgss_offer_effects import ATHLETE_SLOT, offer_effects
from pokemaps_data.pret_hgss_scripts import Instruction, Script
from pokemaps_data.services_characters_hgss import daycare_price


def test_comparison_preserves_starter_and_selects_correlated_team() -> None:
    steps = (
        Instruction(1, "GetStarterChoice", ("0x8000",)),
        Instruction(2, "CompareVarToValue", ("0x8000", "152")),
        Instruction(3, "GoToIf", ("eq", "grass")),
        Instruction(4, "TrainerBattle", ("287", "0", "0", "0")),
        Instruction(5, "End", ()),
        Instruction(6, "TrainerBattle", ("286", "0", "0", "0")),
        Instruction(7, "End", ()),
    )
    script = Script("starter.s", ("entry",), {"entry": 0, "grass": 5}, steps)
    adapted = hgss_flow(script, FlowContext({"eq": 1}, {}, {}))
    battles = resolved_battles({7: adapted})
    grass = next(b for b in battles if b["instruction"] == 5)
    other = next(b for b in battles if b["instruction"] == 3)
    assert {v["starter"] for v in grass["variants"]} == {152}
    assert {v["starter"] for v in other["variants"]} == {155, 158}
    assert adapted.flow.steps[1].writes == frozenset()


def test_athlete_payment_resets_after_each_offer() -> None:
    steps = {
        0: Step(0, "TakeAthletePoints", (50,), None, 1, "pay"),
        1: Step(1, "GiveItem", (17, 1), None, 2, "first"),
        2: Step(2, "GiveItem", (18, 1), None, 3, "second"),
        3: Step(3, "end", (), None, None, "end"),
    }
    flow = ScriptFlow("payments", (0,), steps)
    values = values_at(flow, _is_gift, set(), effects=offer_effects(flow, set()))
    assert values.combos(1, (ATHLETE_SLOT,)) == {(50,)}
    assert values.combos(2, (ATHLETE_SLOT,)) == {(0,)}


def _is_gift(step: Step) -> bool:
    return step.command == "GiveItem"


@pytest.mark.parametrize(
    ("counts", "expected"),
    [((0, 0, 0), (3, 3, 3)), ((98, 98, 98), (1, 1, 1)), ((0, 98, 98), (3, 0, 0)), ((99, 0, 0), (0, 0, 0))],
)
def test_seal_reward_respects_native_early_exit(counts: tuple[int, int, int], expected: tuple[int, int, int]) -> None:
    assert moomoo_seal_quantities(counts) == expected


def test_unresolved_offer_fails_with_native_source() -> None:
    with pytest.raises(ValueError, match=r"unresolved\.s"):
        resolve_quantity_rules(
            [dict(bank=1, command="GiveItem", values=["inconnue", 1], source="unresolved.s", instruction=2)]
        )


@pytest.mark.parametrize(("levels", "price"), [(0, 100), (1, 200), (99, 10000)])
def test_daycare_cost_is_paid_per_level_plus_one(levels: int, price: int) -> None:
    assert daycare_price(levels) == price


def test_gym_appointment_requires_all_native_gates() -> None:
    assert gym_appointment_allowed("SATURDAY", "MORN", "SATURDAY", "MORN", 16, True, False, False)
    assert not gym_appointment_allowed("SATURDAY", "DAY", "SATURDAY", "MORN", 16, True, False, False)
    assert not gym_appointment_allowed("SATURDAY", "MORN", "SATURDAY", "MORN", 15, True, False, False)
    assert not gym_appointment_allowed("SATURDAY", "MORN", "SATURDAY", "MORN", 16, True, True, False)
    assert not gym_appointment_allowed("SATURDAY", "MORN", "SATURDAY", "MORN", 16, True, False, True)


def test_random_partition_keeps_thresholds_without_enumerating_sixty_four_values() -> None:
    flow = ScriptFlow(
        "random",
        (0,),
        {
            0: Step(0, "random", (0x8000, 64), None, 1, "draw"),
            1: Step(1, "compare_value", (0x8000, 32), None, None, "threshold"),
        },
    )
    partition = offer_effects(flow, set()).outputs
    assert {value for _, outputs in partition for _, value in outputs} == {0, 31, 32, 33, 63}
    assert not offer_effects(flow, {0x8000}).outputs
