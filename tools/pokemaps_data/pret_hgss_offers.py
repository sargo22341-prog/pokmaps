"""Offres HGSS : valeurs corrélées, paiements et conditions aux commandes utiles."""

from dataclasses import asdict, replace
from functools import partial

from .pret_gen4_flow import Step, is_var, reachable
from .pret_gen4_flow_chains import Chains
from .pret_gen4_flow_values import (
    COINS_SLOT,
    MONEY_SLOT,
    POINTS_SLOT,
    TAKEN_QUANTITY_SLOT,
    TAKEN_SLOT,
    VERSION_SLOT,
    Choices,
    values_at,
)
from .pret_hgss_flow import HgssFlow
from .pret_hgss_offer_effects import ATHLETE_SLOT, offer_effects, payment_variables


def offer_arguments(command: str, arguments: tuple) -> tuple | None:
    positions = {
        "offer_item": (0, 1),
        "GiveItem": (0, 1),
        "GiveMon": (0, 1, 2, 3),
        "GiveEgg": (0,),
        "LoadNPCTrade": (0,),
        "GiveLoanMon": (0, 1, 2),
        "SpecialMartBuy": (0,),
        "SealMart": (0,),
        "offer_special_mart": (0,),
        "offer_tutor": (0,),
        "MoveTutorInit": (1,),
        "GiveCoins": (0,),
        "GiveAthletePoints": (0,),
        "GiveOrTakeSeal": (0, 1),
        "GiveRibbon": (1,),
        "GiveApricornFromTree": (0, 1),
        "RegisterGearNumber": (0,),
        "GiveBadge": (0,),
    }
    no_args = {
        "offer_mart",
        "MartBuy",
        "offer_heal",
        "HealParty",
        "offer_daycare",
        "offer_daycare_man",
        "PutMonInDaycare",
        "RetrieveDaycareMon",
        "GiveDaycareEgg",
        "GiveTogepiEgg",
        "GiveSpikyEarPichu",
        "MoveRelearnerInit",
        "MonForgetMove",
        "ScrCmd_739",
        "MoveTutorChooseMove",
        "GiveRandomSeal",
        "ScrCmd_771",
        "ScrCmd_772",
        "ScrCmd_555",
        "GivePokedex",
        "GiveRunningShoes",
    }
    if command in no_args:
        return ()
    return tuple(arguments[i] for i in positions[command]) if command in positions else None


def resolved_offers(flows: dict[int, HgssFlow], banks: set[int]) -> list[dict]:
    results = []
    for bank in sorted(banks):
        adapted = flows[bank]
        wanted = {
            s.key: offer_arguments(s.command, s.arguments)
            for s in adapted.flow.steps.values()
            if offer_arguments(s.command, s.arguments) is not None
        }
        if not wanted:
            continue
        chains = Chains(adapted.flow)
        for key, args in wanted.items():
            seeds = {int(arg) for arg in args if is_var(arg)} | payment_variables(adapted.flow)
            effects = offer_effects(adapted.flow, seeds)
            stopped = replace(
                adapted.flow,
                steps={k: replace(s, command="end") if k == key else s for k, s in adapted.flow.steps.items()},
            )
            entries = tuple(entry for entry in stopped.entries if key in reachable(stopped, entry))
            values = values_at(
                stopped,
                partial(_wanted_step, frozenset(wanted)),
                seeds,
                entries=entries,
                choices=Choices(frozenset((152, 155, 158)), frozenset((0, 1)), frozenset((7, 8))),
                effects=effects,
            )
            step = adapted.flow.steps[key]
            for combination in sorted(
                values.combos(
                    key,
                    (
                        *args,
                        VERSION_SLOT,
                        MONEY_SLOT,
                        COINS_SLOT,
                        POINTS_SLOT,
                        ATHLETE_SLOT,
                        TAKEN_SLOT,
                        TAKEN_QUANTITY_SLOT,
                    ),
                ),
                key=repr,
            ):
                results.append(
                    dict(
                        bank=bank,
                        instruction=adapted.original[int(key)],
                        flow_step=key,
                        source=adapted.flow.name,
                        command=step.command,
                        values=list(combination[: len(args)]),
                        version=combination[-7],
                        payments=list(combination[-6:]),
                        conditions=[asdict(condition) for condition in chains.conditions(key)],
                    )
                )
    return results


def _wanted_step(keys: frozenset[int], step: Step) -> bool:
    return step.key in keys
