"""Résolution explicite des identifiants natifs HGSS vers les identifiants PokéAPI."""

from pathlib import Path

from .pokeapi import PokeApi
from .pret_hgss_trainers import item_constants
from .pret_identifiers import item_identifier


class HgssReferences:
    def __init__(self, root: Path, api: PokeApi) -> None:
        self.species = {int(r["id"]): r["identifier"] for r in api.table("pokemon_species") if int(r["id"]) <= 493}
        self.moves = {int(r["id"]): r["identifier"] for r in api.table("moves") if int(r["id"]) <= 467}
        self.move_names = api.names("move_names", "move_id")
        self.item_names = {value: name for name, value in item_constants(root).items()}
        self.items = {
            int(r["game_index"]): int(r["item_id"]) for r in api.table("item_game_indices") if r["generation_id"] == "4"
        }
        self.identifiers = {int(r["id"]): r["identifier"] for r in api.table("items")}

    def item(self, number: int) -> str | None:
        if number == 0:
            return None
        if number in self.items:
            return self.identifiers[self.items[number]]
        name = item_identifier(self.item_names[number].removeprefix("ITEM_"), {})
        compact = {value.replace("-", ""): value for value in self.identifiers.values()}
        if name.replace("-", "") not in compact:
            raise ValueError(f"HGSS : objet natif non représenté : {number} {name}")
        return compact[name.replace("-", "")]
