"""Paiements, conditions et validation des offres DS sans sources externes."""

import pytest

from pokemaps_data.pret_gen4_flow import (
    ADD_ITEM,
    CHECK_FLAG,
    COMPARE_VAR,
    END,
    GOTO,
    GOTO_IF,
    SET_VALUE,
    ScriptFlow,
    Step,
)
from pokemaps_data.pret_gen4_flow_chains import Condition
from pokemaps_data.pret_gen4_flow_requirements import requirements_at
from pokemaps_data.pret_gen4_flow_values import (
    MONEY_SLOT,
    TAKEN_QUANTITY_SLOT,
    TAKEN_SLOT,
    Effects,
    values_at,
)
from pokemaps_data.pret_gen4_offer_bundles import item_bundles
from pokemaps_data.pret_gen4_offer_commands import TAKE_ITEM, OfferCommand
from pokemaps_data.pret_gen4_offer_sites import OfferSite
from pokemaps_data.pret_gen4_offers import Gen4Offer, OfferCatalog, OfferStep, _offer_conditions
from pokemaps_data.validate_offers_gen4 import validate_offers

ITEM, QUANTITY = 0x8004, 0x8005


def test_one_time_gift_keeps_the_flag_it_will_set_after_delivery() -> None:
    condition = Condition("flag:12", "=", 0)
    assert _offer_conditions((condition,), {12}, range(100, 110)) == ((condition,), False)


def test_daily_flag_is_distinct_from_a_permanent_gift_flag() -> None:
    once, daily = Condition("flag:12", "=", 0), Condition("flag:100", "=", 0)
    assert _offer_conditions((once, daily), {12, 100}, range(100, 110)) == ((once,), True)


def test_daily_reset_is_preserved_when_flag_was_set_before_delivery() -> None:
    assert _offer_conditions((), {100}, range(100, 110)) == ((), True)


def _flow(rows: list[tuple[str, tuple[int, ...], int | None]]) -> ScriptFlow:
    steps = {
        i: Step(i, command, args, target, i + 1 if i + 1 < len(rows) else None, str(i))
        for i, (command, args, target) in enumerate(rows)
    }
    return ScriptFlow("test", (0,), steps)


def test_payment_tracks_item_and_count_together() -> None:
    flow = _flow(
        [(SET_VALUE, (ITEM, 72), None), ("take", (ITEM, 10), None), (ADD_ITEM, (338, 1), None), (END, (), None)]
    )
    effects = Effects(payments=(("take", TAKEN_SLOT, 0), ("take", TAKEN_QUANTITY_SLOT, 1)))
    values = values_at(flow, lambda step: step.command == ADD_ITEM, {ITEM}, effects=effects)
    assert values.combos(2, (TAKEN_SLOT, TAKEN_QUANTITY_SLOT)) == frozenset({(72, 10)})


def test_payment_is_cleared_after_receiving_an_offer() -> None:
    flow = _flow([("pay", (200,), None), (ADD_ITEM, (1, 1), None), (ADD_ITEM, (2, 1), None), (END, (), None)])
    values = values_at(
        flow, lambda step: step.command == ADD_ITEM, set(), effects=Effects(payments=(("pay", MONEY_SLOT, 0),))
    )
    assert values.values(1, MONEY_SLOT) == {200}
    assert values.values(2, MONEY_SLOT) == {0}


@pytest.mark.parametrize("pay_first", [True, False])
def test_one_payment_buys_the_whole_bundle(pay_first: bool) -> None:
    gifts = [(ADD_ITEM, (72, 1), None), (ADD_ITEM, (73, 1), None)]
    rows = [("take", (91, 1), None), *gifts] if pay_first else [*gifts, ("take", (91, 1), None)]
    (bundle,) = item_bundles(_flow([*rows, (END, (), None)]), {"take": OfferCommand(TAKE_ITEM)})
    assert bundle.items == ((72, 1), (73, 1))
    assert (bundle.wanted, bundle.quantity) == (91, 1)


def test_join_keeps_only_conditions_required_on_every_path() -> None:
    flow = _flow(
        [
            (CHECK_FLAG, (12,), None),
            (GOTO_IF, (1,), 4),
            (COMPARE_VAR, (ITEM, 1), None),
            (GOTO, (), 4),
            (ADD_ITEM, (1, 1), None),
            (END, (), None),
        ]
    )
    assert requirements_at(flow, 0, lambda step: step.command == ADD_ITEM, None)[4] == ()


def test_condition_before_a_branch_is_preserved() -> None:
    flow = _flow(
        [(CHECK_FLAG, (12,), None), (GOTO_IF, (1,), 3), (END, (), None), (ADD_ITEM, (1, 1), None), (END, (), None)]
    )
    assert requirements_at(flow, 0, lambda step: step.command == ADD_ITEM, None)[3] == (Condition("flag:12", "=", 1),)


@pytest.mark.parametrize(
    "offer",
    [
        Gen4Offer("sale", "ITEM_POTION"),
        Gen4Offer("gift_item", quantity=0),
        Gen4Offer("sale", "ITEM_POTION", price=200, badges=9),
        Gen4Offer("unknown"),
    ],
)
def test_invalid_offer_fails_with_its_location(offer: Gen4Offer) -> None:
    site = OfferSite("PLACE", "object", 0, 1, 2, 0, 0, ())
    catalog = OfferCatalog((OfferStep(site, "test", (offer,), (), False),), ())
    with pytest.raises(ValueError, match="PLACE"):
        validate_offers(catalog, {"PLACE"}, "test")


def test_oversized_initial_domain_fails_before_enumerating() -> None:
    flow = _flow([(ADD_ITEM, (ITEM, QUANTITY), None), (END, (), None)])
    with pytest.raises(ValueError, match="combinaisons initiales"):
        values_at(
            flow,
            lambda step: step.command == ADD_ITEM,
            {ITEM, QUANTITY},
            effects=Effects(initial=((ITEM, tuple(range(1000))), (QUANTITY, tuple(range(1000))))),
        )
