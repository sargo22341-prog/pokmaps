"""Assemblage des tables relatives aux cartes générées."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps import GameMapData
from .maps_characters import CharacterNames, ObjectRow, read_character_names
from .maps_layout import identifier
from .pret_services import PRIZE_VENDOR, VENDING_MACHINE

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Installations (panneaux qui rendent un service) : elles n'ont pas de sprite, leur nom vient de leur type.
FACILITY_KINDS = frozenset({VENDING_MACHINE, PRIZE_VENDOR})


def build_map_tables(builder: DatabaseBuilder) -> dict[str, list[tuple]]:
    vg_ids = {row["identifier"]: int(row["id"]) for row in builder.vg_rows}
    area_ids = {key: area_id for area_id, key in builder.encounters.area_keys.items()}
    known_areas = {row[0] for row in builder.encounters.location_area_table()}
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    objects = _ObjectRows(builder, _ObjectNames(builder, read_character_names()), versions)
    maps, areas, warps, spots = [], [], [], []
    for version_group, data in builder.map_data.items():
        vg = vg_ids[version_group]
        game_maps, game_areas, game_warps, ids = _map_rows(data, vg, area_ids, known_areas, len(warps) + 1)
        maps.extend(game_maps)
        areas.extend(game_areas)
        warps.extend(game_warps)
        for obj in data.objects:
            objects.add(obj, ids[obj.map_const])
        for spot in data.spots:
            spots.append((len(spots) + 1, ids[spot.map_const], spot.kind, spot.x, spot.y))
    if unused := objects.names.unused_text_names():
        raise ValueError(f"npc_text_names.csv : personnages absents des jeux : {unused}")
    return {
        "map": maps,
        "map_area": sorted(set(areas)),
        "map_warp": warps,
        "map_object": objects.objects,
        "trainer_pokemon": objects.parties,
        "npc_offer": objects.offers,
        "map_spot": spots,
    }


class _ObjectRows:
    """Lignes des objets de carte, des équipes de dresseurs et des offres de personnages."""

    def __init__(self, builder: DatabaseBuilder, names: _ObjectNames, versions: dict[str, int]) -> None:
        self.builder = builder
        self.names = names
        self.versions = versions
        self.species = {row["identifier"]: int(row["id"]) for row in builder.species.values()}
        self.objects: list[tuple] = []
        self.parties: list[tuple] = []
        self.offers: list[tuple] = []

    def add(self, obj: ObjectRow, map_id: int) -> None:
        species = self.species
        for name in [obj.pokemon, *(mon[0] for mon in obj.party)] + [
            p for offer in obj.offers for p in (offer.pokemon, offer.wanted)
        ]:
            if name and name not in species:
                raise ValueError(f"Pokémon des cartes inconnu de PokéAPI : {name}")
        object_id = len(self.objects) + 1
        for slot, (pokemon, level, moves) in enumerate(obj.party, start=1):
            move_ids = [self.builder.moves.move_id(move) for move in moves] + [None] * (4 - len(moves))
            self.parties.append((object_id, slot, species[pokemon], level, *move_ids[:4]))
        item_ids = self.builder.items.offer_item_ids
        for offer in obj.offers:
            if offer.version and offer.version not in self.versions:
                raise ValueError(f"Offre d'une version inconnue de PokéAPI : {offer}")
            self.offers.append(
                (
                    len(self.offers) + 1,
                    object_id,
                    offer.kind,
                    offer.item and item_ids[offer.item],
                    offer.pokemon and species[offer.pokemon],
                    offer.quantity,
                    offer.price,
                    offer.wanted and species[offer.wanted],
                    offer.wanted_item and item_ids[offer.wanted_item],
                    offer.version and self.versions[offer.version],
                )
            )
        self.objects.append(
            (
                object_id,
                map_id,
                self.names.characters.npc_kind(obj.sprite) if obj.kind == "npc" else obj.kind,
                obj.x,
                obj.y,
                obj.sprite,
                obj.item and self.builder.items.map_item_ids[obj.item],
                obj.pokemon and species[obj.pokemon],
                obj.level,
                obj.trainer_class,
                self.names.of(obj),
            )
        )


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


class _ObjectNames:
    """Nom affiché de chaque objet de carte : un nom manquant arrête la génération."""

    def __init__(self, builder: DatabaseBuilder, characters: CharacterNames) -> None:
        self.characters = characters
        self.pokemon = builder.api.names("pokemon_species_names", "pokemon_species_id")
        self.species = {row["identifier"]: int(row["id"]) for row in builder.species.values()}
        self.items = builder.api.names("item_names", "item_id")
        self.item_ids = builder.items.map_item_ids
        self.used_texts: set[str] = set()

    def unused_text_names(self) -> list[str]:
        return sorted(set(self.characters.by_text) - self.used_texts)

    def of(self, obj: ObjectRow) -> str:
        if obj.kind == "npc" and obj.text in self.characters.by_text:
            self.used_texts.add(obj.text)
            return self.characters.by_text[obj.text]
        if obj.kind == "trainer" and obj.trainer_class:
            return self.characters.trainer(obj.trainer_class)
        if obj.kind == "pokemon" and obj.pokemon:
            return self.pokemon[self.species[obj.pokemon]]
        if obj.kind in ("item", "hidden_item") and obj.item:
            return self.items[self.item_ids[obj.item]]
        if obj.kind in FACILITY_KINDS:
            return self.characters.facility(obj.kind)
        return self.characters.character(obj.sprite)
