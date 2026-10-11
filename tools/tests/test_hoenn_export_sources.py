"""Variantes des données Hoenn utilisées par la génération explicite."""

import pytest

from pokemaps_data.games import EMERALD, RUBY_SAPPHIRE, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_hoenn_berries import initial_berries
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


@pytest.mark.parametrize("game", (RUBY_SAPPHIRE, EMERALD), ids=lambda game: game.version_group)
def test_prices_ignore_empty_slots_and_resolve_machine_aliases(game: Game, source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    assert "ITEM_NONE" not in repo.prices
    assert repo.prices["ITEM_ULTRA_BALL"] == 1200
    tm = "ITEM_TM10_HIDDEN_POWER" if repo.ruby else "ITEM_TM_HIDDEN_POWER"
    assert repo.prices[tm] == 3000


@pytest.mark.parametrize("game", (RUBY_SAPPHIRE, EMERALD), ids=lambda game: game.version_group)
def test_initial_berries_and_vending_prices_use_each_version(game: Game, source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        berries = initial_berries(repo, version)
        assert berries and set(berries.values()) >= {"ITEM_ORAN_BERRY", "ITEM_PECHA_BERRY"}
        offers = repo.offers[version].read("LilycoveCity_DepartmentStoreRooftop_EventScript_VendingMachine").offers
        sales = {(offer.item, offer.price, offer.currency) for offer in offers if offer.kind == "sale"}
        assert sales == {
            ("ITEM_FRESH_WATER", 200, "money"),
            ("ITEM_SODA_POP", 300, "money"),
            ("ITEM_LEMONADE", 350, "money"),
        }
        gifts = [offer for offer in offers if offer.kind == "gift_item"]
        assert len(gifts) == 6 and all(offer.conditions and offer.price is None for offer in gifts)
