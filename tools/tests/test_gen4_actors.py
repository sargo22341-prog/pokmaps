"""Attribution des offres aux personnages DS et aux scènes, sans sources externes."""

from dataclasses import replace

import pytest

from pokemaps_data.character_actors_gen4 import ActorCatalog, CharacterActor, validate_actors
from pokemaps_data.pret_gen4_offer_sites import OfferSite
from pokemaps_data.pret_gen4_offers import Gen4Offer, OfferCatalog, OfferStep


def _offers(kind: str = "object") -> OfferCatalog:
    site = OfferSite("PLACE", kind, 0, 1, 2, 0, 0, ())
    return OfferCatalog((OfferStep(site, "gift", (Gen4Offer("gift_item", "ITEM_POTION"),), (), False),), ())


def _actor() -> CharacterActor:
    return CharacterActor("pokeplatinum:1:0", "PLACE", 0, 1, 3, 1, 2, 12, 1, (0,))


def test_actor_keeps_his_offer_and_removal_flag() -> None:
    actor = _actor()
    validate_actors(ActorCatalog((actor,), ()), _offers())
    assert actor.hidden_flag == 12


def test_scene_gift_is_not_assigned_to_every_actor() -> None:
    actors = (_actor(), replace(_actor(), key="pokeplatinum:1:1", event=1))
    actors = tuple(replace(actor, offers=()) for actor in actors)
    validate_actors(ActorCatalog(actors, (0,)), _offers("scene"))


@pytest.mark.parametrize(
    "catalog",
    [
        ActorCatalog((_actor(), _actor()), ()),
        ActorCatalog((), ()),
        ActorCatalog((_actor(),), (0,)),
        ActorCatalog((replace(_actor(), event=1),), ()),
        ActorCatalog((replace(_actor(), offers=(1,)),), ()),
        ActorCatalog((replace(_actor(), hidden_flag=-1),), ()),
        ActorCatalog((), (0,)),
    ],
)
def test_missing_repeated_or_misattributed_offer_fails(catalog: ActorCatalog) -> None:
    with pytest.raises(ValueError):
        validate_actors(catalog, _offers())
