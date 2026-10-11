"""Installations interactives GBA portées par un événement de décor."""

from __future__ import annotations

from .maps_characters import ObjectRow
from .maps_characters_data import read_character_names
from .maps_layout_gen3 import Gen3GameMaps
from .maps_offers_gen3 import CATALOG_ONLY_KINDS, mark_alternative_conditions, offer_row
from .pokeapi import PokeApi
from .pret_gen3_offers import Gen3Offer
from .story_events import StoryEvents


def facility_rows(maps: Gen3GameMaps, version: str, api: PokeApi, story: StoryEvents) -> list[ObjectRow]:
    names = read_character_names()
    rows: list[ObjectRow] = []
    reader = maps.repo.offers[version]
    for const in sorted(maps.placements):
        for event in maps.maps[const].bg_events:
            if event.kind != "sign":
                continue
            script = str(event.value("script"))
            result = reader.read(script)
            if result.unresolved:
                raise ValueError(f"{version}:{script} : installation non résolue : {result.unresolved}")
            offers = []
            for offer in result.offers:
                mark_alternative_conditions(offer, maps.repo, version, story)
                if offer.kind not in CATALOG_ONLY_KINDS:
                    offers.append(offer_row(offer, maps.repo, version, api, story))
            if not offers:
                continue
            kind, facility = _facility(script, result.offers)
            rows.append(
                ObjectRow(
                    const,
                    kind,
                    *maps.point(const, event.x, event.y),
                    None,
                    None,
                    None,
                    None,
                    None,
                    offers=offers,
                    version=version,
                    name_fr=names.facility(facility),
                )
            )
    return rows


def _facility(script: str, offers: tuple[Gen3Offer, ...]) -> tuple[str, str]:
    if "VendingMachine" in script:
        return "vending_machine", "vending_machine"
    if {offer.kind for offer in offers} == {"heal"}:
        return "heal_spot", "heal_spot"
    items = {offer.item for offer in offers}
    if items == {"ITEM_PECHA_BERRY"} and all(
        any(filename in offer.source for filename in ("pokeblocks.inc:", "berry_blender.inc:")) for offer in offers
    ):
        return "npc_object", "berry_blender"
    facilities = {
        "ITEM_METEORITE": "meteorite_machine",
        "ITEM_SHOAL_SALT": "shoal_salt",
        "ITEM_SHOAL_SHELL": "shoal_shell",
    }
    if len(items) == 1 and next(iter(items)) in facilities:
        return "npc_object", facilities[next(iter(items))]
    raise ValueError(f"{script} : nom d'installation à relire")
