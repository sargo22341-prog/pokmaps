"""Parcours de tous les lieux des trois versions DS, sans activation dans Android."""

from pathlib import Path

import pytest

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM
from pokemaps_data.maps_layout_gen4 import selected_headers
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.preview_characters_gen4 import character_catalog, validate_character_catalog
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"


@pytest.mark.parametrize("version", ["platinum", "diamond", "pearl"])
def test_every_selected_place_keeps_actors_flags_and_offer_origins(version: str, source_cache_ready: None) -> None:
    game = PLATINUM if version == "platinum" else DIAMOND_PEARL
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    catalog = character_catalog(repo, game)
    validate_character_catalog(catalog)
    headers = selected_headers(repo)
    actors = {(actor.header, actor.event): actor for actor in catalog.actors.actors}
    expected = 0
    for header in headers.values():
        for rank, event in enumerate(repo.events[header.events].object_events):
            expected += 1
            actor = actors[header.constant, rank]
            assert (actor.local_id, actor.graphics, actor.hidden_flag, actor.script) == (
                event.local_id,
                event.graphics,
                event.hidden_flag,
                event.script,
            )
            assert (actor.x, actor.z) == (event.x, event.z)
            assert actor.graphics in catalog.names.sprites
    assert len(actors) == expected
    offers = [
        offer
        for step in catalog.offers.steps
        for offer in step.offers
        if not offer.versions or version in offer.versions
    ]
    assert {"gift_item", "gift_pokemon", "gift_egg", "trade", "fossil", "heal", "point_prize"} <= {
        offer.kind for offer in offers
    }
    assert catalog.actors.scene_offers
    assert all(trainer.party for trainer in catalog.trainers)
    assert sum(label.startswith("offre ") for label in catalog.scenario) == len(catalog.offers.steps)
    assert any(actor.scene_only for actor in catalog.actors.actors)
    assert all(not actor.offers for actor in catalog.actors.actors if actor.scene_only)
    for step in catalog.offers.steps:
        if any(offer.kind == "gift_egg" and offer.pokemon == "SPECIES_RIOLU" for offer in step.offers):
            assert step.giver is not None
            giver = next(actor for actor in catalog.actors.actors if actor.key == step.giver)
            assert catalog.names.sprites[giver.graphics][0] == "Armand"
            assert step.editorial_conditions
    for actor in catalog.actors.actors:
        if catalog.names.sprites[actor.graphics][0] == "Sbire Galaxie":
            assert not any(
                offer.kind == "gift_egg" for index in actor.offers for offer in catalog.offers.steps[index].offers
            )
    assert catalog.names.facilities["accessory_shop"] == "Boutique d’Accessoires"
