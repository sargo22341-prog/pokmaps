"""Domaines bornés des menus et états persistants employés par les offres HGSS."""

from .pret_gen4_flow import ScriptFlow, is_var
from .pret_gen4_flow_values import COINS_SLOT, MONEY_SLOT, POINTS_SLOT, TAKEN_QUANTITY_SLOT, TAKEN_SLOT, Effects

ATHLETE_SLOT = -9


def offer_effects(flow: ScriptFlow, required: set[int]) -> Effects:
    output = []
    menu_var = None
    choices: set[int] = set()
    for step in flow.steps.values():
        args = step.arguments
        if step.command in {"MenuInit", "MenuInitStdGmm", "MenuInitStdGmm2"}:
            menu_var, choices = args[-1], set()
        elif step.command in {"MenuItemAdd", "MenuItemAddWithIcon"}:
            if isinstance(args[-1], int):
                choices.add(args[-1])
        elif step.command == "MenuExec" and isinstance(menu_var, int) and choices:
            output.extend((step.key, ((menu_var, value),)) for value in sorted(choices))
        elif step.command in {"YesNoMenu", "GetMenuChoice"}:
            output.extend((step.key, ((args[0], value),)) for value in (0, 1))
        elif step.command == "random" and args[0] not in required and isinstance(args[1], int):
            boundaries = {0, args[1] - 1}
            for comparison in flow.steps.values():
                if comparison.command == "compare_value" and comparison.arguments[0] == args[0]:
                    value = comparison.arguments[1]
                    if isinstance(value, int):
                        boundaries |= {value - 1, value, value + 1}
            output.extend((step.key, ((args[0], value),)) for value in sorted(boundaries) if 0 <= value < args[1])
    initial = ()
    if any(s.command == "GetFossilPokemon" for s in flow.steps.values()):
        initial = ((0x407F, (138, 140, 142, 345, 347, 408, 410)),)
    return Effects(
        payments=(
            ("SubMoneyImmediate", MONEY_SLOT, 0),
            ("SubMoneyVar", MONEY_SLOT, 0),
            ("TakeCoins", COINS_SLOT, 0),
            ("TakeItem", TAKEN_SLOT, 0),
            ("TakeItem", TAKEN_QUANTITY_SLOT, 1),
            ("ScrCmd_556", POINTS_SLOT, 0),
            ("TakeAthletePoints", ATHLETE_SLOT, 0),
        ),
        initial=initial,
        outputs=tuple(output),
        extra_payment_slots=(ATHLETE_SLOT,),
    )


def payment_variables(flow: ScriptFlow) -> set[int]:
    return {
        int(arg)
        for step in flow.steps.values()
        if step.command in {"SubMoneyVar", "TakeCoins", "TakeItem", "ScrCmd_556", "TakeAthletePoints"}
        for arg in step.arguments[:2]
        if is_var(arg)
    }
