"""Assemblage des tables relatives aux cartes generees."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps import GameMapData, identifier

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
        game_maps, game_areas, game_warps, ids = _map_rows(data, vg, area_ids, known_areas, len(warps) + 1)
        maps.extend(game_maps)
        areas.extend(game_areas)
        warps.extend(game_warps)
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


def _map_rows(
    data: GameMapData,
    version_group_id: int,
    area_ids: dict[str, int],
    known_areas: set[str],
    first_warp_id: int,
) -> tuple[list[tuple], list[tuple[int, int]], list[tuple], dict[str, int]]:
    ids = {row.const: version_group_id * 1000 + row.number for row in data.maps}
    maps = []
    for row in data.maps:
        parent = ids[row.parent] if row.parent else None
        maps.append(
            (
                ids[row.const],
                version_group_id,
                identifier(row.const),
                row.name_fr,
                parent,
                row.x,
                row.y,
                row.width,
                row.height,
                row.level_count,
            )
        )
    areas = []
    for const, area in data.areas:
        if area not in area_ids or area_ids[area] not in known_areas:
            raise ValueError(f"map_areas.csv : zone sans rencontre ou inconnue de PokéAPI : {area}")
        areas.append((ids[const], area_ids[area]))
    warps = []
    for warp_index, warp in enumerate(data.warps, start=first_warp_id):
        target = ids[warp.target] if warp.target else None
        warps.append((warp_index, ids[warp.map_const], warp.x, warp.y, target, warp.target_x, warp.target_y))
    return maps, areas, warps, ids


# --- Écriture -------------------------------------------------------------
