"""Les services de Hoenn gardent leurs coûts et distinguent les lots des dons."""

from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_offers import Gen3Offer, script_offers
from pokemaps_data.pret_gen3_scripts import Gen3Scripts, parse_scripts
from pokemaps_data.sources import pret_dir


def test_casino_keeps_free_dolls_and_coin_gifts_separate_from_purchases() -> None:
    scripts = Gen3Scripts(
        parse_scripts(
            "MauvilleCity_GameCorner_Test:\nremovecoins 1000\nadddecoration DECOR_TREECKO_DOLL\n"
            "addcoins 20\nend\nMauvilleCity_GameCorner_Free:\ngivedecoration DECOR_TREECKO_DOLL\nend",
            "test.inc",
        ),
        {},
    )
    paid, coins = script_offers(scripts, "MauvilleCity_GameCorner_Test").offers
    free = script_offers(scripts, "MauvilleCity_GameCorner_Free").offers[0]
    assert (paid.kind, paid.price, paid.currency) == ("sale_decoration", 1000, "coins")
    assert (coins.kind, coins.quantity, coins.price) == ("gift_coins", "20", None)
    assert free.kind == "gift_decoration" and free.price is None


def test_frontier_cost_survives_the_payment_call_and_unknown_cost_fails() -> None:
    text = (
        "BattleFrontier_ExchangeServiceCorner_Test:\nsetvar VAR_0x8008, 256\n"
        "setvar VAR_0x8009, DECOR_VENUSAUR_DOLL\nspecial TakeFrontierBattlePoints\n"
        "adddecoration VAR_0x8009\nend"
    )
    scripts = Gen3Scripts(parse_scripts(text, "test.inc"), {})
    offer = script_offers(scripts, "BattleFrontier_ExchangeServiceCorner_Test").offers[0]
    assert (offer.item, offer.price, offer.currency) == ("DECOR_VENUSAUR_DOLL", 256, "battle_points")
    scripts = Gen3Scripts(parse_scripts(text.replace("256", "VAR_UNKNOWN"), "test.inc"), {})
    with pytest.raises(ValueError, match="coût de service illisible"):
        script_offers(scripts, "BattleFrontier_ExchangeServiceCorner_Test")


@pytest.mark.parametrize("dialogue_type", ["MSGBOX_YESNO", "5"])
def test_confirmation_answer_does_not_reuse_the_first_menu_choice(dialogue_type: str) -> None:
    text = (
        "Entry:\nmultichoice 0, 0, 1, 0\nswitch VAR_RESULT\ncase 0, Confirm\nend\n"
        f"Confirm:\nmsgbox Question, {dialogue_type}\ngoto_if_eq VAR_RESULT, NO, Cancel\n"
        "giveitem ITEM_POTION\nend\nCancel:\nend"
    )
    scripts = Gen3Scripts(parse_scripts(text, "test.inc"), {})
    assert any(offer.item == "ITEM_POTION" for offer in script_offers(scripts, "Entry").offers)


def _map_offers(repo: Gen3PretRepo, version: str, map_label: str) -> tuple[Gen3Offer, ...]:
    current = next(current for current in repo.maps.values() if current.label == map_label)
    return tuple(
        offer
        for index, event in enumerate(current.objects, 1)
        for offer in repo.offers[version].read_curated_object(map_label, event, index, "ruby-sapphire-emerald").offers
    )


@pytest.mark.parametrize("game_index", [0, 1])
def test_hoenn_services_on_pinned_sources(source_cache_ready: None, game_index: int) -> None:
    game = GEN3_GAMES[game_index]
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        fossils = [offer for offer in _map_offers(repo, version, "RustboroCity_DevonCorp_2F") if offer.required_item]
        assert {(offer.pokemon, offer.quantity, offer.required_item) for offer in fossils} == {
            ("SPECIES_LILEEP", "20", "ITEM_ROOT_FOSSIL"),
            ("SPECIES_ANORITH", "20", "ITEM_CLAW_FOSSIL"),
        }
        glass = _map_offers(repo, version, "Route113_GlassWorkshop")
        assert {(offer.item, offer.price) for offer in glass if offer.currency == "ashes"} == {
            ("ITEM_BLUE_FLUTE", 250),
            ("ITEM_YELLOW_FLUTE", 500),
            ("ITEM_RED_FLUTE", 500),
            ("ITEM_WHITE_FLUTE", 1000),
            ("ITEM_BLACK_FLUTE", 1000),
            ("DECOR_PRETTY_CHAIR", 6000),
            ("DECOR_PRETTY_DESK", 8000),
        }
        assert any(offer.item == "ITEM_SOOT_SACK" and offer.price is None for offer in glass)
        casino = _map_offers(repo, version, "MauvilleCity_GameCorner")
        assert sorted({offer.price for offer in casino if offer.kind == "sale"}) == [1500, 3500, 4000]
        assert len({offer.item for offer in casino if offer.kind == "sale"}) == 5
        assert len({offer.item for offer in casino if offer.kind == "sale_decoration"}) == 3
        assert {(offer.quantity, offer.price) for offer in casino if offer.kind == "sale_coins"} == {
            ("50", 1000),
            ("500", 10000),
        }
        daycare = _map_offers(repo, version, "Route117_PokemonDayCare")
        assert {offer.kind for offer in daycare} >= {"daycare", "daycare_withdrawal"}
        assert any(offer.kind == "daycare_egg" for offer in _map_offers(repo, version, "Route117"))
        relearner = [offer for offer in daycare if offer.kind == "move_relearner"]
        assert not relearner
        _check_relearner(repo, version)
        if version == "emerald":
            _check_frontier(repo)


def _check_relearner(repo: Gen3PretRepo, version: str) -> None:
    offers = tuple(
        offer
        for current in repo.maps.values()
        if current.label.startswith("FallarborTown_")
        for offer in _map_offers(repo, version, current.label)
        if offer.kind == "move_relearner"
    )
    assert offers and all(offer.required_item == "ITEM_HEART_SCALE" for offer in offers)


def _check_frontier(repo: Gen3PretRepo) -> None:
    offers = _map_offers(repo, "emerald", "BattleFrontier_ExchangeServiceCorner")
    assert len({offer.item for offer in offers if offer.kind == "sale_decoration"}) == 15
    assert len({offer.item for offer in offers if offer.kind == "sale"}) == 15
    assert all(offer.currency == "battle_points" and offer.price for offer in offers)
    tutors = [offer for offer in _map_offers(repo, "emerald", "BattleFrontier_Lounge7") if offer.kind == "move_tutor"]
    assert len({offer.move for offer in tutors}) == 20
    assert {offer.price for offer in tutors} == {16, 24, 48}
    ordinary = repo.offers["emerald"].read("MauvilleCity_EventScript_RolloutTutor")
    assert any(offer.move == "MOVE_ROLLOUT" and offer.price is None for offer in ordinary.offers)
    flags = {requirement.subject for offer in ordinary.offers for path in offer.paths for requirement in path}
    assert "FLAG_MOVE_TUTOR_TAUGHT_ROLLOUT" in flags
