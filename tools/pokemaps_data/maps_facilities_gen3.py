"""Installations interactives GBA portées par un événement de décor."""

from __future__ import annotations

from .maps_characters import ObjectRow
from .maps_characters_data import read_character_names
from .maps_layout_gen3 import Gen3GameMaps
from .maps_offers_gen3 import CATALOG_ONLY_KINDS, mark_alternative_conditions, offer_row
from .pokeapi import PokeApi
from .pret_gen3_offers import Gen3Offer
from .pret_models import NpcOffer
from .story_events import StoryEvents


def facility_rows(maps: Gen3GameMaps, version: str, api: PokeApi, story: StoryEvents) -> list[ObjectRow]:
    names = read_character_names()
    rows: list[ObjectRow] = []
    reader = maps.repo.offers[version]
    for const in sorted(maps.placements):
        cells: dict[tuple[str, str], list[tuple[int, int]]] = {}
        offers_of: dict[str, list[NpcOffer]] = {}
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
            cells.setdefault((script, kind), []).append((event.x, event.y))
            offers_of[script] = offers
            if kind != "heal_spot":
                rows.append(_row(maps, const, (event.x, event.y), kind, offers, version, names.facility(facility)))
        for (script, kind), positions in cells.items():
            if kind == "heal_spot":
                for group in _adjacent_groups(positions):
                    rows.append(_bed_row(maps, const, group, offers_of[script], version, names.facility(kind)))
    return rows


def _adjacent_groups(cells: list[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Cases voisines d'un même meuble : un lit de deux ou quatre cases ne fait qu'une installation."""
    pending = sorted(set(cells))
    groups = []
    while pending:
        group = [pending.pop(0)]
        for x, y in group:
            for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if neighbour in pending:
                    pending.remove(neighbour)
                    group.append(neighbour)
        groups.append(sorted(group))
    return groups


def _bed_row(
    maps: Gen3GameMaps, const: str, group: list[tuple[int, int]], offers: list[NpcOffer], version: str, name: str
) -> ObjectRow:
    points = [maps.point(const, x, y) for x, y in group]
    center = (sum(x for x, _ in points) // len(points), sum(y for _, y in points) // len(points))
    return ObjectRow(
        const, "heal_spot", *center, None, None, None, None, None, offers=offers, version=version, name_fr=name
    )


def _row(
    maps: Gen3GameMaps, const: str, cell: tuple[int, int], kind: str, offers: list[NpcOffer], version: str, name: str
) -> ObjectRow:
    return ObjectRow(
        const,
        kind,
        *maps.point(const, *cell),
        None,
        None,
        None,
        None,
        None,
        offers=offers,
        version=version,
        name_fr=name,
    )


def _facility(script: str, offers: tuple[Gen3Offer, ...]) -> tuple[str, str]:
    if script == "FiveIsland_MemorialPillar_EventScript_Memorial":
        return "npc_object", "memorial_pillar"
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
