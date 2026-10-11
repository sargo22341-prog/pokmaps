"""Services de Kanto et des Îles Sevii : coûts, fossiles et conditions uniques."""

from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.maps_facilities_gen3 import _facility
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_offers import Gen3Offer, script_offers
from pokemaps_data.pret_gen3_scripts import Gen3Scripts, parse_scripts
from pokemaps_data.sources import pret_dir


def test_memorial_reward_keeps_its_lemonade_requirement() -> None:
    scripts = Gen3Scripts(
        parse_scripts("FiveIsland_MemorialPillar_Test:\nremoveitem ITEM_LEMONADE\ngiveitem ITEM_TM42\nend", "test.inc"),
        {},
    )
    result = script_offers(scripts, "FiveIsland_MemorialPillar_Test")
    assert result.offers[0].conditions == ("Après avoir déposé une Limonade au Mémorial de Tectonix.",)
    assert _facility("FiveIsland_MemorialPillar_EventScript_Memorial", result.offers) == (
        "npc_object",
        "memorial_pillar",
    )


def test_casino_does_not_turn_coin_gifts_into_purchases() -> None:
    text = "CeladonCity_GameCorner_Test:\naddcoins 50\nremovemoney 1000\nend"
    offer = script_offers(Gen3Scripts(parse_scripts(text, "test.inc"), {}), "CeladonCity_GameCorner_Test").offers[0]
    assert (offer.kind, offer.quantity, offer.price, offer.currency) == ("sale_coins", "50", 1000, "money")
    free = text.replace("removemoney 1000\n", "")
    offer = script_offers(Gen3Scripts(parse_scripts(free, "test.inc"), {}), "CeladonCity_GameCorner_Test").offers[0]
    assert offer.kind == "gift_coins" and offer.price is None
    with pytest.raises(ValueError, match="coût du Casino illisible"):
        script_offers(
            Gen3Scripts(parse_scripts(text.replace("1000", "VAR_UNKNOWN"), "test.inc"), {}),
            "CeladonCity_GameCorner_Test",
        )


def test_remake_move_relearner_describes_both_mushroom_payments() -> None:
    scripts = Gen3Scripts(parse_scripts("TwoIsland_House_Test:\nspecial DisplayMoveTutorMenu\nend", "test.inc"), {})
    offer = script_offers(scripts, "TwoIsland_House_Test").offers[0]
    assert offer.required_item == "ITEM_BIG_MUSHROOM"
    assert offer.conditions == ("Un Gros Champi ou deux Petits Champi par capacité réapprise.",)


def _offers(repo: Gen3PretRepo, version: str, label: str) -> tuple[Gen3Offer, ...]:
    current = next(current for current in repo.maps.values() if current.label == label)
    return tuple(
        offer
        for index, event in enumerate(current.objects, 1)
        for offer in repo.offers[version].read_curated_object(label, event, index, "firered-leafgreen").offers
    )


def test_remake_services_on_pinned_sources(source_cache_ready: None) -> None:
    game = GEN3_GAMES[2]
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        fossils = _offers(repo, version, "CinnabarIsland_PokemonLab_ExperimentRoom")
        assert {(offer.pokemon, offer.quantity, offer.required_item) for offer in fossils if offer.required_item} == {
            ("SPECIES_OMANYTE", "5", "ITEM_HELIX_FOSSIL"),
            ("SPECIES_KABUTO", "5", "ITEM_DOME_FOSSIL"),
            ("SPECIES_AERODACTYL", "5", "ITEM_OLD_AMBER"),
        }
        prizes = _offers(repo, version, "CeladonCity_GameCorner_PrizeRoom")
        pokemon = {offer.pokemon: (offer.price, offer.quantity) for offer in prizes if offer.kind == "prize_pokemon"}
        expected = {
            "firered": {
                "SPECIES_ABRA": (180, "9"),
                "SPECIES_CLEFAIRY": (500, "8"),
                "SPECIES_DRATINI": (2800, "18"),
                "SPECIES_SCYTHER": (5500, "25"),
                "SPECIES_PORYGON": (9999, "26"),
            },
            "leafgreen": {
                "SPECIES_ABRA": (120, "7"),
                "SPECIES_CLEFAIRY": (750, "12"),
                "SPECIES_PINSIR": (2500, "18"),
                "SPECIES_DRATINI": (4600, "24"),
                "SPECIES_PORYGON": (6500, "18"),
            },
        }
        assert pokemon == expected[version]
        assert len({offer.item for offer in prizes if offer.kind == "sale"}) == 10
        coins = _offers(repo, version, "CeladonCity_GameCorner")
        assert {(offer.quantity, offer.price) for offer in coins if offer.kind == "sale_coins"} == {
            ("50", 1000),
            ("500", 10000),
        }
        daycare = _offers(repo, version, "FourIsland_PokemonDayCare")
        assert {offer.kind for offer in daycare} >= {"daycare", "daycare_withdrawal"}
        assert any(offer.kind == "daycare_egg" and offer.conditions for offer in _offers(repo, version, "FourIsland"))
        assert any(offer.kind == "move_deleter" for offer in _offers(repo, version, "FuchsiaCity_House3"))
        seeker = repo.offers[version].read("VermilionCity_PokemonCenter_1F_EventScript_VSSeekerWoman")
        assert any(offer.item == "ITEM_VS_SEEKER" and offer.conditions for offer in seeker.offers)
        tutor = repo.offers[version].read("VictoryRoad_2F_EventScript_DoubleEdgeTutor")
        assert any(offer.move == "MOVE_DOUBLE_EDGE" and offer.price is None for offer in tutor.offers)
        assert any(
            req.subject == "FLAG_TUTOR_DOUBLE_EDGE" and req.operator == "ne" and req.value == "TRUE"
            for offer in tutor.offers
            for path in offer.paths
            for req in path
        )
