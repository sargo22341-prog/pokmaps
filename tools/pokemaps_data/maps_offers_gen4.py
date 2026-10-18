"""Conversion explicite des offres DS, en conservant leurs conditions et leurs paiements composés."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps_characters import ObjectRow
from .pret_identifiers import species_identifier
from .pret_items_gen4 import ds_item_id
from .pret_models import NpcOffer

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .maps_export_gen4 import Gen4MapProjection
    from .pret_gen4_offers import Gen4Offer
    from .preview_characters_gen4 import CharacterCatalog


def item_identifier(builder: DatabaseBuilder, const: str) -> str:
    if const.startswith(("UG_GOOD_", "DECORATION_")):
        raw = const.removeprefix("UG_GOOD_").removeprefix("DECORATION_").replace("__", "_")
        result = "sinnoh-decoration-" + raw.lower().replace("_", "-")
    elif "SEAL" in const and not const.startswith("ITEM_"):
        raw = const.replace("_SEAL_", "_").removeprefix("SEAL_")
        result = "sinnoh-seal-" + raw.lower().replace("_", "-")
    else:
        item_id = ds_item_id(builder, const)
        result = next(name for name, number in builder.items.ids.items() if number == item_id)
    if result not in builder.items.ids:
        raise ValueError(f"Marchandise DS sans nom français : {const}")
    return result


def actor_offers(builder: DatabaseBuilder, catalog: CharacterCatalog, indices: tuple[int, ...]) -> list[NpcOffer]:
    result = []
    for index in indices:
        step = catalog.offers.steps[index]
        label = f"offre {index} {step.site.header} {step.step}"
        stories = catalog.scenario[label][0]
        if step.daily:
            stories = (*stories, "Une fois par jour.")
        for offer in step.offers:
            result += _offers(builder, offer, stories)
    return list(dict.fromkeys(result))


def _offers(builder: DatabaseBuilder, offer: Gen4Offer, stories: tuple[str, ...]) -> list[NpcOffer]:
    kind = {"sale_decoration": "sale", "sale_seal": "sale", "scratch_prize": "gift_item"}.get(offer.kind, offer.kind)
    if offer.kind == "point_prize" and offer.currency == "battle_points":
        kind = "sale"
    if offer.kind == "scratch_prize":
        stories = (*stories, "Gain possible des cartes à gratter, selon le résultat du jeu.")
    if offer.badges is not None:
        stories = (*stories, f"À partir de {offer.badges} badge(s).")
    if offer.move:
        move = builder.moves.move_id(offer.move.removeprefix("MOVE_").lower().replace("_", "-"))
        name = builder.api.names("move_names", "move_id")[move]
        stories = (*stories, f"Capacité enseignée : {name}.")
    components = [("cost", f"{color}-shard", count) for color, count in offer.shards]
    if offer.wanted_item and offer.wanted_quantity:
        components.append(("wanted", item_identifier(builder, offer.wanted_item), offer.wanted_quantity))
    components += [("extra", item_identifier(builder, item), count) for item, count in offer.extra_items]
    return [
        NpcOffer(
            kind,
            item_identifier(builder, offer.item) if offer.item else None,
            species_identifier(offer.pokemon.removeprefix("SPECIES_")) if offer.pokemon else None,
            offer.quantity,
            offer.price,
            species_identifier(offer.wanted.removeprefix("SPECIES_")) if offer.wanted else None,
            item_identifier(builder, offer.wanted_item) if offer.wanted_item else None,
            version,
            currency=None if offer.currency == "shards" else offer.currency,
            stories=stories,
            components=tuple(components),
        )
        for version in offer.versions or (None,)
    ]


def scene_rows(builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection) -> list[ObjectRow]:
    result = []
    for index in catalog.actors.scene_offers:
        step = catalog.offers.steps[index]
        region = projection.maps.by_const[step.site.header]
        point = (
            projection.point(step.site.header, step.site.x, step.site.z)
            if (step.site.x is not None and step.site.z is not None)
            else (region.x + region.width // 2, region.y + region.height // 2)
        )
        offers = actor_offers(builder, catalog, (index,))
        result.append(
            ObjectRow(
                step.site.header,
                "npc",
                *point,
                None,
                None,
                None,
                None,
                None,
                offers=offers,
                name_fr=region.name_fr,
                appearance="npc_object",
            )
        )
    return result
