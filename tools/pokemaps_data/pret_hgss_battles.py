"""Combats HGSS : variantes corrélées au starter, au sexe et à la cartouche."""

from dataclasses import asdict

from .pret_gen4_flow import is_var
from .pret_gen4_flow_chains import Chains
from .pret_gen4_flow_values import GENDER_SLOT, STARTER_SLOT, VERSION_SLOT, Choices, values_at
from .pret_hgss_flow import HgssFlow


def resolved_battles(flows: dict[int, HgssFlow]) -> list[dict]:
    result = []
    choices = Choices(frozenset((152, 155, 158)), frozenset((0, 1)), frozenset((7, 8)))
    for bank, adapted in flows.items():
        if bank == 953:
            continue
        wanted = [s for s in adapted.flow.steps.values() if s.command in {"TrainerBattle", "MultiBattle"}]
        if not wanted:
            continue
        seeds = {int(arg) for step in wanted for arg in step.arguments[:3] if is_var(arg)}
        values = values_at(adapted.flow, wanted.__contains__, seeds, choices=choices)
        chains = Chains(adapted.flow)
        for step in wanted:
            arguments = (
                (step.arguments[0], step.arguments[1], step.arguments[2])
                if step.command == "MultiBattle"
                else (0, step.arguments[0], step.arguments[1])
            )
            variants = []
            for partner, first, second, starter, gender, version in sorted(
                values.combos(step.key, (*arguments, STARTER_SLOT, GENDER_SLOT, VERSION_SLOT)), key=repr
            ):
                if any(not isinstance(value, int) for value in (partner, first, second)):
                    raise ValueError(f"HGSS : équipe variable non résolue : {adapted.flow.name} {step.source}")
                variants.append(
                    dict(
                        opponents=[t for t in (first, second) if t],
                        partner=partner or None,
                        starter=starter if isinstance(starter, int) else None,
                        gender=gender if isinstance(gender, int) else None,
                        version=version if isinstance(version, int) else None,
                    )
                )
            if not variants:
                raise ValueError(f"HGSS : combat jamais atteint : {adapted.flow.name} {step.source}")
            result.append(
                dict(
                    bank=bank,
                    instruction=adapted.original[int(step.key)],
                    source=adapted.flow.name,
                    flow_step=step.key,
                    variants=variants,
                    conditions=[asdict(condition) for condition in chains.conditions(step.key)],
                )
            )
    return result
