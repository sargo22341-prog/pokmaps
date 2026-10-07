"""Tables des attaques : apprentissage, CT / CS et caractéristiques propres à chaque jeu."""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from .pokeapi import optional_int
from .pret_moves import MoveEffect, move_effects, read_pret_moves

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Jusqu'à la 3e génération, la catégorie physique / spéciale d'une attaque dépend de son type.
LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION = 3
DAMAGE_CLASSES = {1: "status", 2: "physical", 3: "special"}

# Attaques dont la constante pret ne correspond pas à l'identifiant PokéAPI (une fois les tirets retirés).
MOVE_ALIASES = {"psychic-m": "psychic", "hi-jump-kick": "high-jump-kick"}

_MOVE_FIELDS = ("type_id", "power", "pp", "accuracy")


class MoveTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    @cached_property
    def pokemon_move_rows(self) -> list[tuple]:
        methods = {int(row["id"]): row["identifier"] for row in self.api.table("pokemon_move_methods")}
        species_of_pokemon = self.builder.species_of_pokemon
        rows = set()
        for row in self.api.table("pokemon_moves"):
            vg = int(row["version_group_id"])
            pokemon_id = int(row["pokemon_id"])
            if vg not in self.builder.vg_ids or pokemon_id not in species_of_pokemon:
                continue
            method = methods[int(row["pokemon_move_method_id"])]
            level = int(row["level"]) if method == "level-up" else 0
            rows.add((species_of_pokemon[pokemon_id], vg, int(row["move_id"]), method, level))
        return sorted(rows)

    @cached_property
    def machine_rows(self) -> list[tuple]:
        return sorted(
            (int(row["version_group_id"]), int(row["item_id"]), int(row["move_id"]))
            for row in self.api.table("machines")
            if int(row["version_group_id"]) in self.builder.vg_ids
        )

    @cached_property
    def moves_by_version_group(self) -> dict[int, set[int]]:
        result: dict[int, set[int]] = defaultdict(set)
        for _, vg, move, _, _ in self.pokemon_move_rows:
            result[vg].add(move)
        for vg, _, move in self.machine_rows:
            result[vg].add(move)
        return result

    def move_table(self) -> list[tuple]:
        names = self.api.names("move_names", "move_id")
        moves = self.api.by_id("moves")
        used = set().union(*self.moves_by_version_group.values())
        return [
            (move, moves[move]["identifier"], names[move], int(moves[move]["generation_id"])) for move in sorted(used)
        ]

    def move_version_group_table(self) -> list[tuple]:
        moves = self.api.by_id("moves")
        # Historique : « avant le groupe de versions X, la valeur était V ».
        changelog: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row in self.api.table("move_changelog"):
            changelog[int(row["move_id"])].append(row)
        rows = []
        for vg in self.builder.vg_ids:
            effects = self.effects[vg]
            for move_id in sorted(self.moves_by_version_group[vg]):
                values = self._values_in(vg, moves[move_id], changelog[move_id])
                type_id = int(values["type_id"])
                effect = effects.get(move_id)
                if effect is None:
                    raise ValueError(f"Attaque {moves[move_id]['identifier']} absente des attaques pret du jeu {vg}")
                rows.append(
                    (
                        move_id,
                        vg,
                        type_id,
                        optional_int(values["power"]),
                        optional_int(values["accuracy"]),
                        int(values["pp"]),
                        self._damage_class(vg, moves[move_id], type_id),
                        effect.description_fr,
                        effect.chance,
                    )
                )
        return rows

    @cached_property
    def effects(self) -> dict[int, dict[int, MoveEffect]]:
        """Effet de chaque attaque, par groupe de versions (id) puis par attaque (id PokéAPI), lu dans pret."""
        missing = [
            row["identifier"] for row in self.builder.vg_rows if row["identifier"] not in self.builder.pret_roots
        ]
        if missing:
            raise ValueError(f"Désassemblage pret manquant pour lire les effets des attaques : {missing}")
        pret_moves = {
            row["identifier"]: read_pret_moves(self.builder.pret_roots[row["identifier"]])
            for row in self.builder.vg_rows
        }
        by_game = move_effects(pret_moves)
        return {
            int(row["id"]): {
                self.move_id(const.lower().replace("_", "-")): effect
                for const, effect in by_game[row["identifier"]].items()
            }
            for row in self.builder.vg_rows
        }

    def _values_in(self, vg: int, move: dict[str, str], changes: list[dict[str, str]]) -> dict[str, str]:
        """Type, puissance, PP et précision de l'attaque dans le groupe de versions `vg`."""
        order = self.builder.vg_order
        values = {name: move[name] for name in _MOVE_FIELDS}
        later = sorted(
            (row for row in changes if order[int(row["changed_in_version_group_id"])] > order[vg]),
            key=lambda row: order[int(row["changed_in_version_group_id"])],
            reverse=True,
        )
        # Du changement le plus récent au plus proche : la dernière valeur écrite est celle du jeu.
        for change in later:
            for name in values:
                if change[name]:
                    values[name] = change[name]
        return values

    def _damage_class(self, vg: int, move: dict[str, str], type_id: int) -> str:
        damage_class = DAMAGE_CLASSES[int(move["damage_class_id"])]
        if self.builder.vg_generation[vg] <= LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION and damage_class != "status":
            return DAMAGE_CLASSES[int(self.builder.type_rows[type_id]["damage_class_id"])]
        return damage_class

    @cached_property
    def move_ids(self) -> dict[str, int]:
        """Identifiant d'attaque (sans tirets) -> id PokéAPI."""
        return {row["identifier"].replace("-", ""): int(row["id"]) for row in self.api.table("moves")}

    def move_id(self, identifier: str) -> int:
        key = MOVE_ALIASES.get(identifier, identifier).replace("-", "")
        if key not in self.move_ids:
            raise ValueError(f"Attaque pret inconnue de PokéAPI : {identifier} (voir MOVE_ALIASES)")
        return self.move_ids[key]
