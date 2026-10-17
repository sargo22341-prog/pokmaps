"""Parcours des offres de Diamant, Perle et Platine dans les dépôts épinglés."""

from pathlib import Path

import pytest

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM
from pokemaps_data.maps_layout_gen4 import selected_headers
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_offer_tables import OfferTables
from pokemaps_data.pret_gen4_offers import Gen4Offer, OfferCatalog, daily_flags, read_offers
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate_offers_gen4 import validate_offers

CACHE = Path(__file__).resolve().parent.parent / ".cache"


@pytest.fixture(scope="module", params=[PLATINUM, DIAMOND_PEARL], ids=lambda game: game.version_group)
def ds(request: pytest.FixtureRequest, source_cache_ready: None) -> tuple[Gen4PretRepo, OfferCatalog]:
    game = request.param
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    headers = selected_headers(repo)
    catalog = read_offers(repo, headers)
    validate_offers(catalog, {header.constant for header in headers.values()}, game.version_group)
    return repo, catalog


def _offers(catalog: OfferCatalog, kind: str) -> set[Gen4Offer]:
    return {offer for step in catalog.steps for offer in step.offers if offer.kind == kind}


def test_gifts_and_eggs_have_their_real_species_and_levels(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    repo, catalog = ds
    eggs = {(offer.pokemon, offer.quantity) for offer in _offers(catalog, "gift_egg")}
    assert ("SPECIES_RIOLU", 1) in eggs
    assert ("SPECIES_TOGEPI", 1) in eggs if repo.platinum else ("SPECIES_HAPPINY", 1) in eggs
    gifts = _offers(catalog, "gift_pokemon")
    assert Gen4Offer("gift_pokemon", pokemon="SPECIES_EEVEE", quantity=20 if repo.platinum else 5) in gifts
    assert any(offer.item == "ITEM_HM03" for offer in _offers(catalog, "gift_item"))


def test_common_shop_stock_unlocks_with_badges(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    _, catalog = ds
    sales = _offers(catalog, "sale")
    assert any(o.item == "ITEM_POKE_BALL" and o.badges == 0 and o.price == 200 for o in sales)
    assert any(o.item == "ITEM_ULTRA_BALL" and o.badges == 5 for o in sales)
    assert {"ITEM_GROWTH_MULCH", "ITEM_DAMP_MULCH", "ITEM_STABLE_MULCH", "ITEM_GOOEY_MULCH"} <= {
        offer.item for offer in sales
    }


def test_trades_and_fossils_use_engine_tables(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    _, catalog = ds
    trades = _offers(catalog, "trade")
    assert len(trades) == 4
    assert Gen4Offer("trade", "ITEM_EVERSTONE", "SPECIES_HAUNTER", wanted="SPECIES_MEDICHAM") in trades
    fossils = _offers(catalog, "fossil")
    assert len(fossils) == 7
    assert Gen4Offer("fossil", "ITEM_ARMOR_FOSSIL", "SPECIES_SHIELDON", 20) in fossils
    assert Gen4Offer("fossil", "ITEM_SKULL_FOSSIL", "SPECIES_CRANIDOS", 20) in fossils


def test_tutors_keep_their_shard_costs(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    repo, catalog = ds
    tutors = _offers(catalog, "move_tutor")
    paid = {offer for offer in tutors if offer.currency == "shards"}
    if not repo.platinum:
        assert not paid
        return
    expected = {(move.move, move.shards) for group in OfferTables(repo).tutors.values() for move in group}
    assert {(offer.move, offer.shards) for offer in paid} == expected
    assert len(paid) == 38


def test_services_and_game_corner_are_exported(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    _, catalog = ds
    kinds = {offer.kind for step in catalog.steps for offer in step.offers}
    assert {"heal", "daycare", "daycare_egg", "daycare_withdrawal", "move_relearner", "move_deleter"} <= kinds
    assert Gen4Offer("move_relearner", wanted_item="ITEM_HEART_SCALE") in _offers(catalog, "move_relearner")
    coins = {(offer.quantity, offer.price) for offer in _offers(catalog, "coin_sale")}
    assert coins == {(50, 1000), (500, 10000)}
    assert all(offer.currency == "coins" and offer.price > 0 for offer in _offers(catalog, "prize_item"))
    assert all(offer.currency == "battle_points" for offer in _offers(catalog, "point_prize"))


def test_daily_rewards_and_persistent_balls(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    repo, catalog = ds
    assert daily_flags(repo)
    daily = {offer.item for step in catalog.steps if step.daily for offer in step.offers}
    assert "ITEM_ORAN_BERRY" in daily
    press = [step for step in catalog.steps if "NEWS_PRESS" in step.site.header]
    balls = {offer.item for step in press for offer in step.offers if offer.quantity == 3}
    assert len(balls) == 12


def test_shard_exchange_preserves_quantity_and_bundles(ds: tuple[Gen4PretRepo, OfferCatalog]) -> None:
    repo, catalog = ds
    exchanges = _offers(catalog, "exchange")
    if repo.platinum:
        shards = [offer for offer in exchanges if offer.wanted_item == "ITEM_STAR_PIECE"]
        assert shards
        assert all(len(offer.extra_items) == 3 and offer.wanted_quantity == 1 for offer in shards)
    else:
        machines = {offer for offer in exchanges if offer.item.startswith("ITEM_TM")}
        assert len(machines) == 4
        assert all(offer.wanted_quantity == 10 for offer in machines)
