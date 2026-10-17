"""Curation DS : figurants temporaires et conditions éditoriales des dons de scène.

Les lignes annotent des événements et offres réellement lus ; elles ne créent ni cadeau ni personnage.
Une référence devenue fausse ou inutilisée bloque l'aperçu, au lieu de masquer la perte d'un service.
"""

from __future__ import annotations

import csv
from dataclasses import replace
from typing import TYPE_CHECKING

from .character_actors_gen4 import assign_actor_offers
from .sources import DATA_DIR
from .story_events import DS_REPOS

if TYPE_CHECKING:
    from .character_actors_gen4 import ActorCatalog
    from .pret_gen4_offers import OfferCatalog, OfferStep


def curate_characters(
    repo: str, family: str, actors: ActorCatalog, offers: OfferCatalog
) -> tuple[ActorCatalog, OfferCatalog]:
    duplicates = _rows("npc_duplicates.csv", "family", {family})
    keys = [row["text"] for row in duplicates]
    if len(keys) != len(set(keys)) or any(not row["reason"].strip() for row in duplicates):
        raise ValueError(f"npc_duplicates.csv : doublon DS répété ou sans raison ({repo})")
    known = {actor.key: actor for actor in actors.actors}
    for key in keys:
        if key not in known:
            raise ValueError(f"npc_duplicates.csv : acteur DS absent : {key}")
        actor = known[key]
        if actor.offers or actor.script not in {0, 65535} or not actor.hidden_flag:
            raise ValueError(f"npc_duplicates.csv : acteur interactif ou permanent à conserver : {key}")
    curated = tuple(replace(actor, scene_only=actor.key in keys) for actor in actors.actors)
    actors = replace(actors, actors=curated)
    rows = _rows("npc_offers.csv", "repos", {repo})
    used: set[int] = set()
    steps = []
    for step in offers.steps:
        conditions = []
        givers = set()
        for index, row in enumerate(rows):
            if _matches(row, step):
                used.add(index)
                conditions.extend(row["conditions"].split("|"))
                if row["expression"] != "script":
                    givers.add(row["expression"])
        if len(givers) > 1:
            raise ValueError(f"npc_offers.csv : donneurs contradictoires : {step.site}")
        steps.append(
            replace(step, editorial_conditions=tuple(dict.fromkeys(conditions)), giver=next(iter(givers), None))
        )
    if unused := [row["text"] for index, row in enumerate(rows) if index not in used]:
        raise ValueError(f"npc_offers.csv : résolutions DS inutilisées : {unused}")
    offers = replace(offers, steps=tuple(steps))
    return assign_actor_offers(actors, offers), offers


def _rows(file: str, column: str, selected: set[str]) -> list[dict[str, str]]:
    with (DATA_DIR / file).open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if set(row[column].split("|")) & selected]
    if file == "npc_offers.csv":
        seen = set()
        for row in rows:
            key = (row["text"], row["source"], row["kind"], row["item"], row["pokemon"])
            if key in seen or not set(row["repos"].split("|")) <= DS_REPOS or row["action"] != "resolve":
                raise ValueError(f"{file} : résolution DS répétée ou invalide : {key}")
            if not row["reason"].strip() or not row["source"] or not row["conditions"]:
                raise ValueError(f"{file} : résolution DS sans source, raison ou conditions : {key}")
            if not row["expression"] or not row["text"]:
                raise ValueError(f"{file} : résolution DS sans événement ou attribution : {key}")
            fields = ("quantity", "price", "wanted_item", "required_flag")
            if any(row.get(field) for field in fields):
                raise ValueError(f"{file} : annotation DS qui modifierait une offre du moteur : {key}")
            phrases = row["conditions"].split("|")
            if any(
                not phrase or phrase != phrase.strip() or not phrase[0].isupper() or phrase.endswith(".")
                for phrase in phrases
            ):
                raise ValueError(f"{file} : condition DS mal formée : {key}")
            seen.add(key)
    return rows


def _matches(row: dict[str, str], step: OfferStep) -> bool:
    site = step.site
    if row["text"] != f"{site.header}:{site.kind}:{site.event}" or row["source"] != step.step:
        return False
    return any(
        offer.kind == row["kind"]
        and (not row["item"] or offer.item == row["item"])
        and (not row["pokemon"] or offer.pokemon == row["pokemon"])
        and (not row["move"] or offer.move == row["move"])
        for offer in step.offers
    )
