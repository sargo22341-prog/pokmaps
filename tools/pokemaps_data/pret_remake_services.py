"""Objets requis, tarifs et services propres à Rouge Feu et Vert Feuille."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .pret_gen3_script_values import number_value

if TYPE_CHECKING:
    from .pret_gen3_conditions import ScriptState
    from .pret_gen3_offers import Gen3Offer
    from .pret_gen3_scripts import Gen3Scripts


def describe_remake_offer(offer: Gen3Offer, state: ScriptState, scripts: Gen3Scripts) -> Gen3Offer:
    label = state.point[0]
    if label.startswith("FiveIsland_MemorialPillar_") and offer.item == "ITEM_TM42":
        return replace(offer, conditions=("Après avoir déposé une Limonade au Mémorial de Tectonix.",))
    if label.startswith("CinnabarIsland_PokemonLab_ExperimentRoom_") and offer.kind == "gift_pokemon":
        fossils = {
            "SPECIES_OMANYTE": "ITEM_HELIX_FOSSIL",
            "SPECIES_KABUTO": "ITEM_DOME_FOSSIL",
            "SPECIES_AERODACTYL": "ITEM_OLD_AMBER",
        }
        if offer.pokemon not in fossils:
            raise ValueError(f"{offer.source} : fossile de Cramois'Île inconnu : {offer.pokemon}")
        return replace(
            offer,
            required_item=fossils[offer.pokemon],
            conditions=("Confier le fossile au scientifique, sortir du laboratoire puis revenir.",),
        )
    if label.startswith("CeladonCity_GameCorner_"):
        return _casino_offer(offer, state, scripts)
    if label.startswith("FourIsland_"):
        return _daycare_offer(offer)
    if label.startswith("TwoIsland_House_") and offer.kind == "move_relearner":
        return replace(
            offer,
            required_item="ITEM_BIG_MUSHROOM",
            conditions=("Un Gros Champi ou deux Petits Champi par capacité réapprise.",),
        )
    if offer.item == "ITEM_VS_SEEKER":
        return replace(offer, conditions=("Charger le Cherche VS en faisant 100 pas pour demander une revanche.",))
    return offer


def _casino_offer(offer: Gen3Offer, state: ScriptState, scripts: Gen3Scripts) -> Gen3Offer:
    if offer.kind in {"gift_item", "gift_pokemon"} and state.point[0].startswith("CeladonCity_GameCorner_PrizeRoom_"):
        kind = "prize_pokemon" if offer.kind == "gift_pokemon" else "sale"
        return _purchase(offer, kind, state.value("VAR_TEMP_2"), "coins", scripts)
    if offer.kind != "gift_coins":
        return offer
    payments = [line for line in scripts.blocks[state.point[0]].lines if line.command == "removemoney"]
    if not payments:
        return offer
    if len(payments) != 1:
        raise ValueError(f"{offer.source} : plusieurs paiements de jetons dans le même bloc")
    return _purchase(offer, "sale_coins", state.value(payments[0].args[0]), "money", scripts)


def _purchase(offer: Gen3Offer, kind: str, value: str, currency: str, scripts: Gen3Scripts) -> Gen3Offer:
    price = number_value(value, scripts.constants)
    if price is None or not 0 < price <= 65535:
        raise ValueError(f"{offer.source} : coût du Casino illisible : {value}")
    return replace(offer, kind=kind, price=price, currency=currency, conditions=("Posséder la Boîte Jetons.",))


def _daycare_offer(offer: Gen3Offer) -> Gen3Offer:
    if offer.kind == "daycare":
        return replace(
            offer, conditions=("La Pension de l'Île 4 garde deux Pokémon pour les élever et les reproduire.",)
        )
    if offer.kind == "daycare_withdrawal":
        return replace(offer, currency="money", conditions=("Retrait : 100 ₽ plus 100 ₽ par niveau gagné.",))
    if offer.kind == "daycare_egg":
        return replace(
            offer, conditions=("Œuf des parents compatibles confiés à la Pension ; garder une place dans l'équipe.",)
        )
    return offer
