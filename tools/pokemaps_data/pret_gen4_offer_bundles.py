"""Lots d'objets échangés ensemble, y compris quand le paiement suit les dons."""

from __future__ import annotations

from dataclasses import dataclass

from .pret_gen4_flow import ADD_ITEM, Key, ScriptFlow, is_var
from .pret_gen4_offer_commands import TAKE_ITEM, OfferCommand


@dataclass(frozen=True)
class ItemBundle:
    start: Key
    steps: frozenset[Key]
    items: tuple[tuple[int, int], ...]
    wanted: int
    quantity: int


def item_bundles(flow: ScriptFlow, commands: dict[str, OfferCommand]) -> tuple[ItemBundle, ...]:
    payments = {name for name, command in commands.items() if command.kind == TAKE_ITEM}
    predecessors = {step.following: step for step in flow.steps.values() if step.following is not None}
    consumed: set[Key] = set()
    bundles = []
    for step in flow.steps.values():
        if step.command != ADD_ITEM or step.key in consumed:
            continue
        chain = [step]
        for _ in range(16):
            following = flow.steps.get(chain[-1].following)
            if following is None or following.command != ADD_ITEM:
                break
            chain.append(following)
        else:
            raise ValueError(f"{flow.name} : lot de plus de seize objets")
        if len(chain) < 2:
            continue
        before, after = predecessors.get(step.key), flow.steps.get(chain[-1].following)
        payment = next((p for p in (before, after) if p is not None and p.command in payments), None)
        if payment is None:
            continue
        pairs = tuple((s.arguments[0], s.arguments[1]) for s in chain)
        values = (*payment.arguments[:2], *(value for pair in pairs for value in pair))
        if any(not isinstance(value, int) or is_var(value) or value <= 0 for value in values):
            raise ValueError(f"{flow.name} : lot échangé non constant : {step.source}")
        keys = frozenset(s.key for s in chain)
        bundles.append(ItemBundle(step.key, keys, pairs, payment.arguments[0], payment.arguments[1]))
        consumed |= keys
    return tuple(bundles)
