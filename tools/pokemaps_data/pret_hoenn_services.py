"""Coûts et conditions des services de Hoenn, conservés dans l'aperçu GBA."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .pret_gen3_script_values import number_value

if TYPE_CHECKING:
    from .pret_gen3_conditions import ScriptState
    from .pret_gen3_offers import Gen3Offer
    from .pret_gen3_scripts import Gen3Scripts


def describe_hoenn_offer(offer: Gen3Offer, state: ScriptState, scripts: Gen3Scripts) -> Gen3Offer:
    label = state.point[0]
    if label.startswith("MauvilleCity_GameCorner_"):
        return _casino_offer(offer, state, scripts)
    if label.startswith("BattleFrontier_ExchangeServiceCorner_") and offer.kind in {"gift_item", "gift_decoration"}:
        return _purchase(offer, state.value("VAR_0x8008"), "battle_points", scripts)
    if (
        label.startswith("Route113_GlassWorkshop_")
        and offer.item != "ITEM_SOOT_SACK"
        and offer.kind in {"gift_item", "gift_decoration"}
    ):
        return _glass_offer(offer, scripts)
    if label.startswith("RustboroCity_DevonCorp_2F_") and offer.kind == "gift_pokemon":
        return _fossil_offer(offer)
    if label.startswith(("Route117_", "FallarborTown_")):
        return _service_offer(offer)
    return offer


def _purchase(offer: Gen3Offer, value: str, currency: str, scripts: Gen3Scripts) -> Gen3Offer:
    price = number_value(value, scripts.constants)
    if price is None or not 0 < price <= 65535:
        raise ValueError(f"{offer.source} : coût de service illisible : {value}")
    kind = {"gift_item": "sale", "gift_decoration": "sale_decoration", "gift_coins": "sale_coins"}[offer.kind]
    return replace(offer, kind=kind, price=price, currency=currency)


def _casino_offer(offer: Gen3Offer, state: ScriptState, scripts: Gen3Scripts) -> Gen3Offer:
    if offer.kind not in {"gift_item", "gift_decoration", "gift_coins"}:
        return offer
    command = "removemoney" if offer.kind == "gift_coins" else "removecoins"
    payments = [line for line in scripts.blocks[state.point[0]].lines if line.command == command]
    if not payments:
        return offer
    if len(payments) != 1:
        raise ValueError(f"{offer.source} : plusieurs paiements dans le même bloc")
    currency = "money" if command == "removemoney" else "coins"
    result = _purchase(offer, state.value(payments[0].args[0]), currency, scripts)
    return replace(result, conditions=("Posséder la Boîte Jetons.",))


def _glass_offer(offer: Gen3Offer, scripts: Gen3Scripts) -> Gen3Offer:
    # La branche différée redonne un objet déjà payé : le tarif vient de la branche de fabrication.
    prices: set[int] = set()
    for label, block in scripts.blocks.items():
        if not label.startswith("Route113_GlassWorkshop_"):
            continue
        if not any(line.command == "setvar" and line.args == ("VAR_0x8008", offer.item) for line in block.lines):
            continue
        for line in block.lines:
            if line.command == "subvar" and line.args[0] == "VAR_ASH_GATHER_COUNT":
                price = number_value(line.args[1], scripts.constants)
                if price is None:
                    raise ValueError(f"{line.source} : coût en cendres illisible")
                prices.add(price)
    if len(prices) != 1:
        raise ValueError(f"{offer.source} : tarif de l'Atelier du Verre absent ou ambigu : {offer.item}")
    result = _purchase(offer, str(prices.pop()), "ashes", scripts)
    return replace(
        result,
        conditions=("Collecter les cendres avec le Sac à Suie.", "Un lot en attente a déjà été payé en cendres."),
    )


def _fossil_offer(offer: Gen3Offer) -> Gen3Offer:
    fossils = {"SPECIES_LILEEP": "ITEM_ROOT_FOSSIL", "SPECIES_ANORITH": "ITEM_CLAW_FOSSIL"}
    if offer.pokemon not in fossils:
        raise ValueError(f"{offer.source} : fossile Devon inconnu : {offer.pokemon}")
    return replace(
        offer,
        required_item=fossils[offer.pokemon],
        conditions=("Confier le fossile au scientifique de Devon, puis revenir lorsque la restauration est prête.",),
    )


def _service_offer(offer: Gen3Offer) -> Gen3Offer:
    match offer.kind:
        case "daycare":
            return replace(
                offer, conditions=("La Pension peut garder deux Pokémon pour les élever et les reproduire.",)
            )
        case "daycare_withdrawal":
            return replace(offer, currency="money", conditions=("Retrait : 100 ₽ plus 100 ₽ par niveau gagné.",))
        case "daycare_egg":
            return replace(
                offer,
                conditions=("Œuf issu des Pokémon compatibles confiés à la Pension ; garder une place dans l'équipe.",),
            )
        case "move_relearner":
            return replace(
                offer, required_item="ITEM_HEART_SCALE", conditions=("Une Écaille Cœur par capacité réapprise.",)
            )
        case _:
            return offer
