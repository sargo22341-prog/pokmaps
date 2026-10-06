"""Assemblage des tables relatives aux cartes generees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps import identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


def build_map_tables(builder: DatabaseBuilder) -> dict[str, list[tuple]]:
    vg_ids = {row["identifier"]: int(row["id"]) for row in builder.vg_rows}
    area_ids = {key: area_id for area_id, key in builder.area_keys.items()}
    species = {row["identifier"]: int(row["id"]) for row in builder.species.values()}
    known_areas = {row[0] for row in builder.location_area_table()}
    maps, areas, warps, objects, parties, offers, spots = [], [], [], [], [], [], []
    for version_group, data in builder.map_data.items():
        vg = vg_ids[version_group]
        ids = {row.const: vg * 1000 + row.number for row in data.maps}
        for row in data.maps:
            parent = ids[row.parent] if row.parent else None
            maps.append(
                (ids[row.const], vg, identifier(row.const), row.name_fr, parent, row.x, row.y, row.width,
                 row.height, row.level_count)
            )  # fmt: skip
        for const, area in data.areas:
            if area not in area_ids or area_ids[area] not in known_areas:
                raise ValueError(f"map_areas.csv : zone sans rencontre ou inconnue de PokéAPI : {area}")
            areas.append((ids[const], area_ids[area]))
        for warp in data.warps:
            target = ids[warp.target] if warp.target else None
            warps.append(
                (len(warps) + 1, ids[warp.map_const], warp.x, warp.y, target, warp.target_x, warp.target_y)
            )
        for obj in data.objects:
            for name in [obj.pokemon, *(mon[0] for mon in obj.party)] + [
                p for offer in obj.offers for p in (offer.pokemon, offer.wanted)
            ]:
                if name and name not in species:
                    raise ValueError(f"Pokémon des cartes inconnu de PokéAPI : {name}")
            object_id = len(objects) + 1
            for slot, (pokemon, level, moves) in enumerate(obj.party, start=1):
                move_ids = [builder.move_id(move) for move in moves] + [None] * (4 - len(moves))
                parties.append((object_id, slot, species[pokemon], level, *move_ids[:4]))
            for offer in obj.offers:
                offers.append(
                    (
                        len(offers) + 1,
                        object_id,
                        offer.kind,
                        offer.item and builder.offer_item_ids[offer.item],
                        offer.pokemon and species[offer.pokemon],
                        offer.quantity,
                        offer.price,
                        offer.wanted and species[offer.wanted],
                    )
                )
            objects.append(
                (
                    len(objects) + 1,
                    ids[obj.map_const],
                    obj.kind,
                    obj.x,
                    obj.y,
                    obj.sprite,
                    obj.item and builder.map_item_ids[obj.item],
                    obj.pokemon and species[obj.pokemon],
                    obj.level,
                    obj.trainer_class,
                )
            )
        for spot in data.spots:
            spots.append((len(spots) + 1, ids[spot.map_const], spot.kind, spot.x, spot.y))
    return {
        "map": maps,
        "map_area": sorted(set(areas)),
        "map_warp": warps,
        "map_object": objects,
        "trainer_pokemon": parties,
        "npc_offer": offers,
        "map_spot": spots,
    }

# --- Écriture -------------------------------------------------------------

