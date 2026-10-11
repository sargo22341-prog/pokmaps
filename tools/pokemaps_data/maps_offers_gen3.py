"""Conversion des offres Hoenn vers les modèles de la base embarquée."""

from __future__ import annotations

from .maps_items_gen3 import _identifier
from .pokeapi import PokeApi
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_conditions import ScriptRequirement
from .pret_gen3_offers import Gen3Offer
from .pret_identifiers import species_identifier
from .pret_models import NpcOffer
from .story_events import StoryEvents

# Les décorations et la Baie Enigma personnalisée sont conservées dans le catalogue,
# leur interface dédiée relève de la phase 8 du plan génération 3.
CATALOG_ONLY_KINDS = frozenset({"sale_decoration", "gift_decoration", "gift_custom_item", "national_dex"})
_KINDS = {"rename_pokemon": "name_rater", "sale_coins": "coin_sale", "gift_coins": "coin_gift"}
_SERVICES = frozenset({"heal", "name_rater", "daycare", "daycare_egg", "daycare_withdrawal", "move_deleter"})


def offer_row(offer: Gen3Offer, repo: Gen3PretRepo, version: str, api: PokeApi, story: StoryEvents) -> NpcOffer:
    constants = repo.offers[version].scripts.constants
    item = _identifier(offer.item, constants) if offer.item else None
    pokemon = species_identifier(offer.pokemon.removeprefix("SPECIES_")) if offer.pokemon else None
    wanted = species_identifier(offer.wanted.removeprefix("SPECIES_")) if offer.wanted else None
    required = _identifier(offer.required_item, constants) if offer.required_item else None
    kind = _KINDS.get(offer.kind, offer.kind)
    if kind == "gift_pokemon" and required:
        kind, item, required = "fossil", required, None
    if kind == "sale" and offer.currency == "coins":
        kind = "prize_item"
    quantity = int(offer.quantity, 0) if offer.quantity else None
    if kind in _SERVICES or kind == "move_tutor":
        quantity = None
    requirements = frozenset(
        ScriptRequirement(req.subject, req.operator, str(constants.get(req.value, req.value)))
        for req in (frozenset.intersection(*offer.paths) if offer.paths else frozenset())
    )
    phrases = (*story.script_phrases(repo_name(repo), requirements, offer.source), *offer.conditions)
    if offer.move:
        move = offer.move.removeprefix("MOVE_").lower().replace("_", "-")
        move_id = next(int(row["id"]) for row in api.table("moves") if row["identifier"] == move)
        phrases += (api.names("move_names", "move_id")[move_id],)
    if offer.eligible_pokemon:
        species = species_identifier(offer.eligible_pokemon.removeprefix("SPECIES_"))
        species_id = next(int(row["id"]) for row in api.table("pokemon_species") if row["identifier"] == species)
        phrases += (api.names("pokemon_species_names", "pokemon_species_id")[species_id],)
    price = repo.prices[offer.item] if kind == "sale" and offer.price is None else offer.price
    return NpcOffer(
        kind,
        item,
        pokemon,
        quantity,
        price,
        wanted,
        required,
        version,
        currency=offer.currency,
        stories=tuple(dict.fromkeys(phrases)),
    )


def repo_name(repo: Gen3PretRepo) -> str:
    return "pokefirered" if repo.remake else ("pokeruby" if repo.ruby else "pokeemerald")


def mark_alternative_conditions(offer: Gen3Offer, repo: Gen3PretRepo, version: str, story: StoryEvents) -> None:
    """Les branches alternatives consomment leur curation sans devenir des conditions communes."""
    name = repo_name(repo)
    constants = repo.offers[version].scripts.constants
    for path in offer.paths:
        described = set()
        for requirement in path:
            normalized = ScriptRequirement(
                requirement.subject, requirement.operator, str(constants.get(requirement.value, requirement.value))
            )
            if (name, normalized) in story.values or (name, normalized.subject) in story.events:
                described.add(normalized)
        story.script_phrases(name, frozenset(described), offer.source)
