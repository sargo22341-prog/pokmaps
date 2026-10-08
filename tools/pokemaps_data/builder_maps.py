"""Assemblage des tables relatives aux cartes générées."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .games import Game, complete_families
from .map_spots import Point, TerrainKey, read_spots
from .maps import GameMapData
from .maps_characters import ObjectRow
from .maps_characters_data import CharacterNames, read_character_names
from .maps_layout import identifier
from .offer_conditions import ALL_TIMES, ALL_WEEKDAYS
from .pret_models import NpcOffer
from .pret_services import HEAL_SPOT, PRIZE_VENDOR, VENDING_MACHINE
from .story_events import StoryEvents, read_story_events

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Installations (panneaux qui rendent un service) : elles n'ont pas de sprite, leur nom vient de leur clé
# (npc_text_names.csv) ou de leur type (facility_names.csv).
FACILITY_KINDS = frozenset({VENDING_MACHINE, PRIZE_VENDOR, HEAL_SPOT})
# Apparence d'un personnage qui est un Pokémon (npc_names.csv) : son cri le nomme mieux que son sprite.
_POKEMON_CHARACTER = "npc_pokemon"


def build_map_tables(builder: DatabaseBuilder) -> dict[str, list[tuple]]:
    vg_ids = {row["identifier"]: int(row["id"]) for row in builder.vg_rows}
    area_ids = builder.locations.area_ids
    known_areas = builder.encounters.used_areas
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    objects = _ObjectRows(builder, _ObjectNames(builder, read_character_names()), versions, read_story_events())
    maps, areas, warps = [], [], []
    spots = _SpotRows(read_spots(), builder.games)
    repos = {game.version_group: game.pret_repo for game in builder.games}
    for version_group, data in builder.map_data.items():
        vg = vg_ids[version_group]
        game_maps, game_areas, game_warps, ids = _map_rows(data, vg, area_ids, known_areas, len(warps) + 1)
        maps.extend(game_maps)
        areas.extend(game_areas)
        warps.extend(game_warps)
        for obj in data.objects:
            objects.add(obj, ids[obj.map_const], repos[version_group])
        spots.add_game(version_group, data, ids)
    families = set(complete_families(builder.games))
    spots.check_all_used(families)
    if unused := objects.names.unused_text_names(families):
        raise ValueError(f"npc_text_names.csv : personnages absents des jeux : {unused}")
    if unused := objects.story.unused(set(repos.values())):
        raise ValueError(f"story_events.csv : drapeaux qu'aucune offre n'exige : {unused}")
    return {
        "map": maps,
        "map_area": sorted(set(areas)),
        "map_warp": warps,
        "map_object": objects.objects,
        "trainer_pokemon": objects.parties,
        "npc_offer": objects.offers,
        "npc_offer_story": objects.stories,
        "map_spot": spots.rows,
    }


class _SpotRows:
    """Emplacements des Pokémon sauvages : ceux de la génération, sauf les terrains retouchés dans map_spots.csv."""

    def __init__(self, curated: dict[TerrainKey, frozenset[Point]], games: tuple[Game, ...]) -> None:
        self.curated = curated
        self.families = {game.version_group: game.map_family for game in games}
        self.used: set[TerrainKey] = set()
        self.rows: list[tuple] = []

    def add_game(self, version_group: str, data: GameMapData, ids: dict[str, int]) -> None:
        family = self.families[version_group]
        for spot in data.spots:
            if TerrainKey(family, identifier(spot.map_const), spot.kind) not in self.curated:
                self.rows.append((len(self.rows) + 1, ids[spot.map_const], spot.kind, spot.x, spot.y))
        bounds = {identifier(row.const): (ids[row.const], row) for row in data.maps}
        # Un terrain n'a d'emplacements générés que si le jeu y fait apparaître des Pokémon sauvages.
        terrains = {(identifier(spot.map_const), spot.kind) for spot in data.spots}
        for key, points in sorted(self.curated.items()):
            if key.family != family or key.map_identifier not in bounds:
                continue
            if (key.map_identifier, key.kind) not in terrains:
                where = f"{key.kind} de {key.map_identifier} ({version_group})"
                raise ValueError(f"map_spots.csv : aucun Pokémon sauvage n'apparaît sur le terrain {where}")
            self.used.add(key)
            map_id, _ = bounds[key.map_identifier]
            # Les jeux d'une famille partagent leurs retouches, pas toujours leurs plans (la Caverne Azurée de Jaune) :
            # chaque emplacement doit tomber au centre d'une case du terrain dans chacun d'eux.
            if outside := sorted(points - data.terrain.get((key.map_identifier, key.kind), frozenset())):
                where = f"{key.kind} de {key.map_identifier} ({version_group})"
                raise ValueError(f"map_spots.csv : emplacements hors des cases du terrain {where} : {outside}")
            for x, y in sorted(points):
                self.rows.append((len(self.rows) + 1, map_id, key.kind, x, y))

    def check_all_used(self, families: set[str]) -> None:
        """Chaque terrain retouché d'une famille dont tous les jeux sont construits doit servir à l'un d'eux."""
        if unknown := sorted(key for key in set(self.curated) - self.used if key.family in families):
            raise ValueError(f"map_spots.csv : cartes absentes des jeux de leur famille : {unknown}")


class _ObjectRows:
    """Lignes des objets de carte, des équipes de dresseurs et des offres de personnages."""

    def __init__(
        self, builder: DatabaseBuilder, names: _ObjectNames, versions: dict[str, int], story: StoryEvents
    ) -> None:
        self.builder = builder
        self.names = names
        self.versions = versions
        self.story = story
        self.species = {row["identifier"]: int(row["id"]) for row in builder.species.values()}
        self.objects: list[tuple] = []
        self.parties: list[tuple] = []
        self.offers: list[tuple] = []
        self.stories: list[tuple] = []

    def add(self, obj: ObjectRow, map_id: int, repo: str) -> None:
        if obj.version and obj.version not in self.versions:
            raise ValueError(f"Objet de carte d'une version inconnue de PokéAPI : {obj}")
        species = self.species
        for name in [obj.pokemon, obj.cry, *(mon[0] for mon in obj.party)] + [
            p for offer in obj.offers for p in (offer.pokemon, offer.wanted)
        ]:
            if name and name not in species:
                raise ValueError(f"Pokémon des cartes inconnu de PokéAPI : {name}")
        object_id = len(self.objects) + 1
        for slot, (pokemon, level, moves) in enumerate(obj.party, start=1):
            move_ids = [self.builder.moves.move_id(move) for move in moves] + [None] * (4 - len(moves))
            self.parties.append((object_id, slot, species[pokemon], level, *move_ids[:4]))
        for offer in obj.offers:
            self._add_offer(obj, object_id, offer, repo)
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
                obj.version and self.versions[obj.version],
            )
        )

    def _add_offer(self, obj: ObjectRow, object_id: int, offer: NpcOffer, repo: str) -> None:
        """Ligne de l'offre, avec ses moments, ses jours et les étapes du scénario qu'elle exige."""
        if offer.version and offer.version not in self.versions:
            raise ValueError(f"Offre d'une version inconnue de PokéAPI : {offer}")
        condition = offer.condition
        where = f"{obj.map_const}, {obj.key}, {offer.kind} {offer.item or offer.pokemon or ''}".rstrip()
        if not condition.possible:
            raise ValueError(f"Offre jamais possible d'après ses conditions ({where}) : {condition}")
        offer_id = len(self.offers) + 1
        item_ids = self.builder.items.offer_item_ids
        self.offers.append(
            (
                offer_id,
                object_id,
                offer.kind,
                offer.item and item_ids[offer.item],
                offer.pokemon and self.species[offer.pokemon],
                offer.quantity,
                offer.price,
                offer.wanted and self.species[offer.wanted],
                offer.wanted_item and item_ids[offer.wanted_item],
                offer.version and self.versions[offer.version],
                None if condition.times == ALL_TIMES else condition.times,
                None if condition.weekdays == ALL_WEEKDAYS else condition.weekdays,
            )
        )
        for slot, phrase in enumerate(self.story.phrases(repo, condition, where), start=1):
            self.stories.append((offer_id, slot, phrase))


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
                int(row.is_world),
                ids[row.origin] if row.origin else None,
                ids[row.start] if row.start else None,
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
        self.items = builder.items
        self.used_texts: set[str] = set()

    def unused_text_names(self, families: set[str]) -> list[str]:
        """Personnages nommés par leur texte, d'une famille de `families`, qu'aucun objet de carte n'a employés."""
        texts = {text for text, family in self.characters.text_families.items() if family in families}
        return sorted(texts - self.used_texts)

    def of(self, obj: ObjectRow) -> str:
        """Nom relu par clé, sinon d'après la nature de l'objet : classe du dresseur, Pokémon, objet, type
        d'installation, cri du Pokémon pour un personnage qui en a l'apparence, ou sprite du personnage."""
        if obj.kind in ("npc", *FACILITY_KINDS) and obj.key in self.characters.by_text:
            self.used_texts.add(obj.key)
            return self.characters.by_text[obj.key]
        if obj.kind == "trainer" and obj.trainer_class:
            return self.characters.trainer(obj.trainer_class)
        if obj.kind == "pokemon" and obj.pokemon:
            return self.pokemon[self.species[obj.pokemon]]
        if obj.kind in ("item", "hidden_item") and obj.item:
            return self.items.name_of(obj.item)
        if obj.kind in FACILITY_KINDS:
            return self.characters.facility(obj.kind)
        if obj.cry and self.characters.npc_kind(obj.sprite) == _POKEMON_CHARACTER:
            return self.pokemon[self.species[obj.cry]]
        return self.characters.character(obj.sprite)
