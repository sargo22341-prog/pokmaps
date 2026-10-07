"""Tables des objets : CT / CS, objets d'évolution, Poké Balls, objets des cartes et objets tenus."""

from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
from typing import TYPE_CHECKING

from .games import Game, PretFormat
from .pokeapi import FRENCH, clean_text
from .pret_identifiers import item_identifier, species_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Catégories d'objets toujours incluses (en plus des objets d'évolution et des CT/CS) : les Poké Balls, dont les
# Balls fabriquées par Fargas avec des Noigrumes à partir de la 2e génération.
BALL_CATEGORIES = ("standard-balls", "special-balls", "apricorn-balls")

# Objets tenus des Pokémon sauvages de la 2e génération (LoadEnemyMon, engine/battle/core.asm) : pas d'objet si un
# tirage sur 256 est inférieur à « 75 percent + 1 », puis l'objet 2 si un second tirage est inférieur à « 8 percent »,
# « n percent » valant n * 255 // 100. Soit 23 % pour l'objet 1 et 2 % pour l'objet 2, comme le dit le moteur.
_GEN2_HELD_ITEM_256 = 256 - (75 * 255 // 100 + 1)
_GEN2_SECOND_ITEM_256 = 8 * 255 // 100
_NO_ITEM = "NO_ITEM"
# Première génération dont PokéAPI donne les objets tenus (pokemon_items).
_POKEAPI_HELD_ITEMS_GENERATION = 3
# Objets tenus absents de PokéAPI, écartés parce qu'aucun Pokémon sauvage ne peut les tenir : la Berserk Gene n'est
# tenue que par Mewtwo, qu'on ne rencontre pas dans Or et Argent. Une rencontre de ce Pokémon arrête la génération.
_HELD_ITEMS_WITHOUT_WILD_HOLDER = frozenset({"BERSERK_GENE"})


class ItemTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    @cached_property
    def item_rows(self) -> list[tuple[int, str, str, str]]:
        names = self.api.names("item_names", "item_id")
        items = self.api.by_id("items")
        categories = {int(row["id"]): row["identifier"] for row in self.api.table("item_categories")}
        used = {item for _, item, _ in self.builder.moves.machine_rows}
        used |= set(self.map_item_ids.values())
        used |= set(self.offer_item_ids.values())
        used |= {item for _, _, item, _ in self.pokemon_item_rows}
        for row in self.builder.pokemon.evolution_rows:
            used |= {item for item in (row[6], row[7]) if item}
        # Poké Balls existant dans au moins une des générations configurées.
        ball_ids = {item_id for item_id, row in items.items() if categories[int(row["category_id"])] in BALL_CATEGORIES}
        for row in self.api.table("item_game_indices"):
            if int(row["item_id"]) in ball_ids and int(row["generation_id"]) in self.builder.generations:
                used.add(int(row["item_id"]))
        return [
            (item_id, items[item_id]["identifier"], names[item_id], categories[int(items[item_id]["category_id"])])
            for item_id in sorted(used)
        ]

    @cached_property
    def pokemon_item_rows(self) -> list[tuple[int, int, int, int]]:
        """Objets tenus par les Pokémon sauvages de chaque version : (espèce, version, objet, probabilité en %).

        PokéAPI ne les donne qu'à partir de la 3e génération ; avant, le format pret du jeu décide : la 1re génération
        n'en a pas, ceux de la 2e sont lus dans pret."""
        rows: list[tuple[int, int, int, int]] = []
        for game, vg in zip(self.builder.games, self.builder.vg_ids, strict=True):
            if self.builder.vg_generation[vg] >= _POKEAPI_HELD_ITEMS_GENERATION:
                rows += self._pokeapi_held_items(vg)
                continue
            match game.pret_format:
                case PretFormat.GEN1:
                    pass
                case PretFormat.GEN2:
                    rows += self._pret_held_items(game, vg)
        return sorted(rows)

    def _pokeapi_held_items(self, vg: int) -> list[tuple[int, int, int, int]]:
        species_of_pokemon = self.builder.species_of_pokemon
        versions = {int(row["id"]) for row in self.builder.version_rows if int(row["version_group_id"]) == vg}
        rows = []
        for row in self.api.table("pokemon_items"):
            pokemon_id, version = int(row["pokemon_id"]), int(row["version_id"])
            if version in versions and pokemon_id in species_of_pokemon:
                rarity = int(row["rarity"])
                if not 0 < rarity <= 100:
                    raise ValueError(f"Probabilité d'objet tenu invalide : {dict(row)}")
                rows.append((species_of_pokemon[pokemon_id], version, int(row["item_id"]), rarity))
        return rows

    def _pret_held_items(self, game: Game, vg: int) -> list[tuple[int, int, int, int]]:
        """Objets 1 et 2 des données de base de chaque Pokémon (pret), avec les probabilités du moteur."""
        repo = self.builder.gen2_repo(game, "les objets tenus")
        species = {row["identifier"]: species_id for species_id, row in self.builder.species.items()}
        item_ids = {row["identifier"]: int(row["id"]) for row in self.api.table("items")}
        versions = [int(row["id"]) for row in self.builder.version_rows if int(row["version_group_id"]) == vg]
        wild = {
            self.builder.species_of_pokemon[int(row["pokemon_id"])] for row in self.builder.encounters.raw_encounters
        }
        rows = []
        for const, (first, second) in sorted(repo.wild_held_items.items()):
            pokemon = species[species_identifier(const)]
            chances: dict[int, float] = {}
            for item, chance_256 in ((first, 256 - _GEN2_SECOND_ITEM_256), (second, _GEN2_SECOND_ITEM_256)):
                if item in _HELD_ITEMS_WITHOUT_WILD_HOLDER and pokemon in wild:
                    raise ValueError(f"{const} se rencontre dans {game.version_group} : son objet {item} doit exister")
                if item == _NO_ITEM or item in _HELD_ITEMS_WITHOUT_WILD_HOLDER:
                    continue
                identifier = item_identifier(item, repo.machines)
                if identifier not in item_ids:
                    raise ValueError(f"Objet tenu inconnu de PokéAPI : {item} (voir pret_identifiers.ITEM_ALIASES)")
                share = _GEN2_HELD_ITEM_256 * chance_256 / 256 / 256 * 100
                chances[item_ids[identifier]] = chances.get(item_ids[identifier], 0) + share
            rows += [
                (pokemon, version, item, round(chance)) for item, chance in chances.items() for version in versions
            ]
        return rows

    def item_descriptions(self) -> dict[int, str]:
        """Description française de chaque objet (texte du jeu le plus ancien qui en a une), sauf CT / CS."""
        machines = {item for _, item, _ in self.builder.moves.machine_rows}
        best: dict[int, tuple[int, str]] = {}
        for row in self.api.table("item_flavor_text"):
            if int(row["language_id"]) != FRENCH:
                continue
            item_id = int(row["item_id"])
            order = self.builder.vg_order.get(int(row["version_group_id"]), 0)
            if item_id not in machines and (item_id not in best or order < best[item_id][0]):
                best[item_id] = (order, clean_text(row["flavor_text"]))
        return {item_id: text for item_id, (_, text) in best.items()}

    @cached_property
    def offer_item_ids(self) -> dict[str, int]:
        """Objets donnés, vendus, gagnés ou demandés en échange par les personnages : identifiant PokéAPI -> id."""
        identifiers = {
            item
            for data in self.builder.map_data.values()
            for obj in data.objects
            for offer in obj.offers
            for item in (offer.item, offer.wanted_item)
            if item
        }
        return self._known_items(identifiers, "Objets des personnages")

    @cached_property
    def map_item_ids(self) -> dict[str, int]:
        """Objets posés sur les cartes : identifiant PokéAPI -> id."""
        identifiers = {obj.item for data in self.builder.map_data.values() for obj in data.objects if obj.item}
        return self._known_items(identifiers, "Objets des cartes")

    def _known_items(self, identifiers: Iterable[str], label: str) -> dict[str, int]:
        ids = {row["identifier"]: int(row["id"]) for row in self.api.table("items")}
        unknown = sorted(set(identifiers) - ids.keys())
        if unknown:
            raise ValueError(f"{label} inconnus de PokéAPI : {unknown} (voir pret_identifiers.ITEM_ALIASES)")
        return {identifier: ids[identifier] for identifier in identifiers}
