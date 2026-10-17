"""Acteurs DS conservés par lieu et étape, avec provenance des dons de scène.

Une apparence commune n'identifie pas une personne : deux PNJ avec le même sprite ne sont pas des doublons.
Les exemplaires de scénario restent distincts et gardent leur drapeau de retrait. Une offre lancée par une
scène reste attribuée à la scène, sans l'affecter arbitrairement à tous les personnages qui y participent.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header
    from .pret_gen4_offers import OfferCatalog


@dataclass(frozen=True)
class CharacterActor:
    key: str
    header: str
    event: int
    local_id: int
    graphics: int
    x: int
    z: int
    hidden_flag: int
    script: int
    offers: tuple[int, ...]
    scene_only: bool = False


@dataclass(frozen=True)
class ActorCatalog:
    actors: tuple[CharacterActor, ...]
    # Offres sans donneur posé, lancées par des scènes, cases ou déclencheurs.
    scene_offers: tuple[int, ...]


def read_actors(repo: Gen4PretRepo, headers: dict[int, Gen4Header], offers: OfferCatalog) -> ActorCatalog:
    prefix = "pokeplatinum" if repo.platinum else "pokediamond"
    actors = []
    for index, header in sorted(headers.items()):
        for rank, obj in enumerate(repo.events[header.events].object_events):
            actors.append(
                CharacterActor(
                    f"{prefix}:{index}:{rank}",
                    header.constant,
                    rank,
                    obj.local_id,
                    obj.graphics,
                    obj.x,
                    obj.z,
                    obj.hidden_flag,
                    obj.script,
                    (),
                )
            )
    catalog = assign_actor_offers(ActorCatalog(tuple(actors), ()), offers)
    validate_actors(catalog, offers)
    return catalog


def validate_actors(catalog: ActorCatalog, offers: OfferCatalog) -> None:
    keys = [actor.key for actor in catalog.actors]
    if len(keys) != len(set(keys)):
        raise ValueError("Personnages DS : clé de personnage répétée")
    assigned = list(catalog.scene_offers)
    for actor in catalog.actors:
        if actor.scene_only and (actor.offers or actor.script not in {0, 65535} or not actor.hidden_flag):
            raise ValueError(f"{actor.key} : acteur interactif ou permanent écarté")
        if actor.hidden_flag < 0:
            raise ValueError(f"{actor.key} : drapeau de retrait négatif")
        for index in actor.offers:
            if not 0 <= index < len(offers.steps):
                raise ValueError(f"{actor.key} : numéro d'offre inconnu : {index}")
            site = offers.steps[index].site
            giver = offers.steps[index].giver
            correct = giver == actor.key if giver is not None else (site.kind, site.event) == ("object", actor.event)
            if site.header != actor.header or not correct:
                raise ValueError(f"{actor.key} : offre attribuée à un autre personnage")
        assigned.extend(actor.offers)
    if sorted(assigned) != list(range(len(offers.steps))):
        raise ValueError("Personnages DS : offre sans origine ou attribuée plusieurs fois")
    for index in catalog.scene_offers:
        if offers.steps[index].site.kind == "object" or offers.steps[index].giver is not None:
            raise ValueError(f"Personnages DS : offre de PNJ attribuée à une scène : {index}")


def assign_actor_offers(catalog: ActorCatalog, offers: OfferCatalog) -> ActorCatalog:
    by_key = {actor.key: [] for actor in catalog.actors}
    by_event = {(actor.header, actor.event): actor.key for actor in catalog.actors}
    scenes = []
    for index, step in enumerate(offers.steps):
        giver = step.giver
        if giver is None and step.site.kind == "object":
            giver = by_event.get((step.site.header, step.site.event))
            if giver is None:
                raise ValueError(f"{step.site.header} : événement de PNJ absent : {step.site.event}")
        if giver is not None:
            if giver not in by_key:
                raise ValueError(f"{step.site.header} : donneur absent : {giver}")
            by_key[giver].append(index)
        else:
            scenes.append(index)
    return ActorCatalog(
        tuple(replace(actor, offers=tuple(by_key[actor.key])) for actor in catalog.actors), tuple(scenes)
    )
