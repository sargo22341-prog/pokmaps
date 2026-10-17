"""Validation des offres DS exportées dans l'aperçu des personnages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pret_gen4_offers import Gen4Offer, OfferCatalog

_KINDS = frozenset(
    {
        "gift_item",
        "gift_pokemon",
        "gift_egg",
        "sale",
        "trade",
        "fossil",
        "heal",
        "move_tutor",
        "move_deleter",
        "move_relearner",
        "daycare",
        "daycare_egg",
        "daycare_withdrawal",
        "accessory_shop",
        "sale_decoration",
        "sale_seal",
        "point_prize",
        "prize_item",
        "exchange",
        "coin_gift",
        "coin_sale",
        "scratch_cards",
        "scratch_prize",
    }
)
_PAID = frozenset({"sale", "point_prize", "prize_item", "coin_sale", "scratch_cards"})
_CURRENCIES = frozenset({None, "money", "coins", "battle_points", "shards"})
_ITEMS = frozenset(
    {
        "gift_item",
        "sale",
        "sale_decoration",
        "sale_seal",
        "point_prize",
        "prize_item",
        "exchange",
        "fossil",
        "scratch_prize",
    }
)


def validate_offers(catalog: OfferCatalog, headers: set[str], where: str) -> None:
    if not catalog.steps:
        raise ValueError(f"{where} : catalogue d'offres vide")
    keys = []
    for step in catalog.steps:
        site = step.site
        label = f"{where}, {site.header}, {step.step}"
        if site.header not in headers or not step.offers:
            raise ValueError(f"{label} : offre vide ou hors des lieux retenus")
        keys.append((site, step.step))
        if len(step.offers) != len(set(step.offers)):
            raise ValueError(f"{label} : offre répétée")
        for offer in step.offers:
            _validate_offer(offer, label)
    if len(keys) != len(set(keys)):
        raise ValueError(f"{where} : étape d'offre répétée")


def _validate_offer(offer: Gen4Offer, where: str) -> None:
    if offer.kind not in _KINDS or offer.currency not in _CURRENCIES:
        raise ValueError(f"{where} : nature ou monnaie inconnue : {offer}")
    if offer.kind in _PAID and (offer.price is None or offer.price <= 0):
        raise ValueError(f"{where} : offre payante sans prix positif : {offer}")
    if offer.quantity is not None and offer.quantity <= 0:
        raise ValueError(f"{where} : quantité ou niveau non positif : {offer}")
    if offer.badges is not None and not 0 <= offer.badges <= 8:
        raise ValueError(f"{where} : nombre de badges invalide : {offer}")
    if offer.kind in {"gift_pokemon", "gift_egg", "trade", "fossil"} and not offer.pokemon:
        raise ValueError(f"{where} : Pokémon manquant : {offer}")
    if offer.kind == "trade" and not offer.wanted:
        raise ValueError(f"{where} : Pokémon demandé manquant : {offer}")
    if offer.kind == "move_tutor" and not offer.move:
        raise ValueError(f"{where} : capacité du tuteur manquante : {offer}")
    if offer.currency == "shards" and (not offer.shards or any(count <= 0 for _, count in offer.shards)):
        raise ValueError(f"{where} : coût en Tessons invalide : {offer}")
    if offer.kind in _ITEMS and not offer.item:
        raise ValueError(f"{where} : objet manquant : {offer}")
    if offer.kind in {"exchange", "move_relearner"} and not offer.wanted_item:
        raise ValueError(f"{where} : objet demandé manquant : {offer}")
    if offer.wanted_quantity is not None and offer.wanted_quantity <= 0:
        raise ValueError(f"{where} : quantité demandée non positive : {offer}")
    if any(not item or count <= 0 for item, count in offer.extra_items):
        raise ValueError(f"{where} : lot d'objets invalide : {offer}")
    if not set(offer.versions) <= {"diamond", "pearl", "platinum"}:
        raise ValueError(f"{where} : version inconnue : {offer}")
