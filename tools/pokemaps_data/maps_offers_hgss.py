"""Offres HGSS : quantités, coûts et conditions conservés depuis les étapes résolues."""

from dataclasses import replace

from .offers_persistent_hgss import persistent_offers
from .pret_models import NpcOffer
from .references_hgss import HgssReferences

_INFORMATION = frozenset(
    {
        "RegisterGearNumber",
        "GiveBadge",
        "GiveRibbon",
        "GiveOrTakeSeal",
        "ScrCmd_771",
        "ScrCmd_772",
        "GivePokedex",
        "GiveRunningShoes",
        "ScrCmd_739",
        "GiveRandomSeal",
    }
)


def actor_offers(actor: dict, catalog: dict, refs: HgssReferences) -> list[NpcOffer]:
    result = []
    for step in catalog["service_steps"]:
        if not any(a["header"] == actor["header"] and a["event"] == actor["event"] for a in step["actors"]):
            continue
        version = {7: "heartgold", 8: "soulsilver", "externe": None}[step["version"]]
        offers = _step_offers(step, catalog, refs)
        offers = [_paid_offer(offer, step["costs"], refs) for offer in offers]
        result.extend(
            replace(o, version=version, stories=tuple(dict.fromkeys((*step["conditions_fr"], *o.stories))))
            for o in offers
        )
    result.extend(persistent_offers(actor, catalog, refs))
    return list(dict.fromkeys(result))


def _paid_offer(offer: NpcOffer, costs: list[dict], refs: HgssReferences) -> NpcOffer:
    if not costs:
        return offer
    if len(costs) != 1 or offer.kind not in {"gift_item", "gift_pokemon"}:
        raise ValueError(f"HGSS : paiement non représenté : {offer} {costs}")
    cost = costs[0]
    if cost["currency"] == "item":
        item = refs.item(cost["item"])
        return replace(offer, kind="exchange", wanted_item=item, components=(("wanted", item, cost["amount"]),))
    if cost["currency"] == "coins":
        kind = "prize_pokemon" if offer.pokemon else "prize_item"
    elif cost["currency"] in {"money", "battle_points"}:
        kind = "sale"
    else:
        raise ValueError(f"HGSS : monnaie sans conversion d'offre : {cost['currency']}")
    return replace(offer, kind=kind, price=cost["amount"], currency=cost["currency"])


def _step_offers(step: dict, catalog: dict, refs: HgssReferences) -> list[NpcOffer]:
    command, values = step["command"], step["values"]
    if command in _INFORMATION:
        return []
    if step.get("kind") == "apricorn_return":
        return [
            NpcOffer(
                "gift_item",
                item=refs.item(c["item"]),
                quantity=1,
                stories=("Fargas : quantité égale au dépôt de Noigrumes ; remise le jour suivant.",),
            )
            for c in catalog["apricorns"]["conversions"]
        ]
    if command in {"GiveItem", "offer_item"}:
        return [NpcOffer("gift_item", item=refs.item(values[0]), quantity=values[1])]
    if command in {"GiveMon", "GiveLoanMon"}:
        return [
            NpcOffer(
                "gift_pokemon",
                pokemon=refs.species[values[0]],
                quantity=values[1],
                item=refs.item(values[2]) if len(values) > 2 else None,
            )
        ]
    if command in {"GiveEgg", "GiveTogepiEgg", "GiveSpikyEarPichu"}:
        species = 175 if command == "GiveTogepiEgg" else 172 if command == "GiveSpikyEarPichu" else values[0]
        return [
            NpcOffer(
                "gift_pokemon" if command == "GiveSpikyEarPichu" else "gift_egg",
                pokemon=refs.species[species],
                quantity=30 if command == "GiveSpikyEarPichu" else 1,
                external_event=command == "GiveSpikyEarPichu",
            )
        ]
    if command in {"HealParty", "offer_heal"}:
        return [NpcOffer("heal")]
    if command in {"offer_mart", "offer_special_mart"}:
        stock = (
            catalog["shops"]["ordinary"] if command == "offer_mart" else catalog["shops"]["special"][values[0]]["items"]
        )
        return [
            NpcOffer(
                "sale",
                item=refs.item(r["item"]),
                quantity=1,
                price=r["price"],
                currency="money",
                stories=(f"À partir de {r['minimum_badges']} badge(s).",) if r.get("minimum_badges") else (),
            )
            for r in stock
        ]
    return _service_offer(command, values, catalog, refs)


def _service_offer(command: str, values: list, catalog: dict, refs: HgssReferences) -> list[NpcOffer]:
    if command == "LoadNPCTrade":
        trade = next(r for r in catalog["trades"] if r["index"] == values[0])
        return [
            NpcOffer(
                "trade",
                pokemon=refs.species[trade["given"]],
                wanted=refs.species[trade["requested"]],
                quantity=trade.get("level", 1),
                item=refs.item(trade.get("item", 0)),
            )
        ]
    if command in {"MoveTutorInit", "offer_tutor"}:
        return _tutors(command, values, catalog, refs)
    if command == "MonForgetMove":
        return [NpcOffer("move_deleter")]
    if command == "MoveRelearnerInit":
        return [
            NpcOffer(
                "move_relearner",
                wanted_item=refs.item(catalog["services"]["relearner"]["item"]),
                stories=("Une Écaille Cœur après réapprentissage réussi.",),
            )
        ]
    raise ValueError(f"HGSS : commande d'offre sans conversion : {command}")


def _tutors(command: str, values: list, catalog: dict, refs: HgssReferences) -> list[NpcOffer]:
    if command == "MoveTutorInit":
        return [NpcOffer("move_tutor", stories=("Capacité enseignée : " + refs.move_names[values[0]],))]
    tutors = catalog["tutors"]
    if command == "offer_tutor":
        npc = (
            "MOVE_TUTOR_NPC_FRONTIER_TOP_LEFT",
            "MOVE_TUTOR_NPC_FRONTIER_TOP_RIGHT",
            "MOVE_TUTOR_NPC_FRONTIER_BOTTOM_RIGHT",
        )[values[0]]
        tutors = [r for r in tutors if r["npc"] == npc]
    result = []
    for row in tutors:
        result.append(
            NpcOffer(
                "move_tutor",
                price=row["cost"] or None,
                currency=None if not row["cost"] else row["currency"],
                stories=(
                    "Capacité enseignée : "
                    + refs.move_names[
                        next(
                            n
                            for n, key in refs.moves.items()
                            if key.replace("-", "_").upper() == row["move"].removeprefix("MOVE_")
                        )
                    ],
                ),
            )
        )
    return result
