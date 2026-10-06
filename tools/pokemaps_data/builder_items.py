"""Table des objets : CT / CS, objets d'évolution, Poké Balls et objets présents sur les cartes."""

from __future__ import annotations

from collections.abc import Iterable
from functools import cached_property
from typing import TYPE_CHECKING

from .pokeapi import FRENCH, clean_text

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Catégories d'objets toujours incluses (en plus des objets d'évolution et des CT/CS).
BALL_CATEGORIES = ("standard-balls", "special-balls")


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
        """Objets donnés ou vendus par les personnages : identifiant PokéAPI -> id."""
        identifiers = {
            offer.item
            for data in self.builder.map_data.values()
            for obj in data.objects
            for offer in obj.offers
            if offer.item
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
            raise ValueError(f"{label} inconnus de PokéAPI : {unknown} (voir maps.ITEM_ALIASES)")
        return {identifier: ids[identifier] for identifier in identifiers}
