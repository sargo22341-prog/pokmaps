"""Tables des attaques : apprentissage, CT / CS et caractéristiques propres à chaque jeu."""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from .builder_form_moves import deoxys_move_versions
from .games import Game, PretFormat
from .pokeapi import optional_int
from .pret_moves import GameMoves, MoveEffect, PretMove, move_effects, read_pret_moves

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Jusqu'à la 3e génération, la catégorie physique / spéciale d'une attaque dépend de son type.
LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION = 3
DAMAGE_CLASSES = {1: "status", 2: "physical", 3: "special"}

# Attaques dont la constante pret ne correspond pas à l'identifiant PokéAPI (une fois les tirets retirés).
MOVE_ALIASES = {
    "psychic-m": "psychic",
    "hi-jump-kick": "high-jump-kick",
    "faint-attack": "feint-attack",
    "smelling-salt": "smelling-salts",
}

_MOVE_FIELDS = ("type_id", "power", "pp", "accuracy")

# Méthodes d'apprentissage écrites dans la base (pokemon_move.method) : toute autre arrête la génération.
LEARN_METHODS = frozenset(
    {
        "level-up",
        "machine",
        "egg",
        "tutor",
        # Électacle de Pichu, né d'un parent qui tient un Ballon Lumière (Émeraude).
        "light-ball-egg",
        # Surf du Pikachu Surfeur de Pokémon Stadium : événement externe (Rouge, Bleu et Jaune).
        "stadium-surfing-pikachu",
    }
)


class MoveTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    @cached_property
    def pokemon_move_rows(self) -> list[tuple]:
        methods = {int(row["id"]): row["identifier"] for row in self.api.table("pokemon_move_methods")}
        species_of_pokemon = self.builder.species_of_pokemon
        rows = set(self._form_move_versions)
        for row in self.api.table("pokemon_moves"):
            vg = int(row["version_group_id"])
            pokemon_id = int(row["pokemon_id"])
            if pokemon_id == 386 and vg in {key[1] for key in self._form_move_versions}:
                continue
            if vg not in self.builder.vg_ids or pokemon_id not in species_of_pokemon:
                continue
            method = methods[int(row["pokemon_move_method_id"])]
            if method not in LEARN_METHODS:
                raise ValueError(f"Méthode d'apprentissage inconnue : {method} ({dict(row)})")
            level = int(row["level"]) if method == "level-up" else 0
            rows.add((species_of_pokemon[pokemon_id], vg, int(row["move_id"]), method, level))
        return sorted(rows)

    @cached_property
    def _form_move_versions(self) -> dict[tuple, frozenset[int]]:
        return deoxys_move_versions(self.builder)

    def pokemon_move_table(self) -> list[tuple]:
        rows = []
        for key in self.pokemon_move_rows:
            versions = self._form_move_versions.get(key, frozenset())
            if key[3] not in LEARN_METHODS:
                raise ValueError(f"Méthode d'apprentissage de forme inconnue : {key}")
            group_versions = {
                int(row["id"]) for row in self.builder.version_rows if int(row["version_group_id"]) == key[1]
            }
            specific = versions != group_versions and bool(versions)
            if specific and len(versions) != 1:
                raise ValueError(f"Apprentissage partagé par un sous-ensemble de versions non représentable : {key}")
            rows.append((*key, next(iter(versions)) if specific else None))
        return rows

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

    @cached_property
    def types_outside_the_chart(self) -> frozenset[int]:
        """Types d'attaque absents du tableau des types (builder.type_rows) : « ??? », celui de Malédiction de la
        2e à la 4e génération. Il n'a ni efficacité ni catégorie : Malédiction est une attaque de statut."""
        moves = self.api.by_id("moves")
        return (
            frozenset(
                int(self._values_in(vg, moves[move_id], self._changelog[move_id])["type_id"])
                for vg, move_ids in self.moves_by_version_group.items()
                for move_id in move_ids
            )
            - self.builder.type_rows.keys()
        )

    @cached_property
    def _changelog(self) -> dict[int, list[dict[str, str]]]:
        """Historique de chaque attaque : « avant le groupe de versions X, la valeur était V »."""
        changelog: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row in self.api.table("move_changelog"):
            changelog[int(row["move_id"])].append(row)
        return changelog

    def machine_types(self) -> dict[int, int]:
        """CT / CS -> type de son attaque dans le premier jeu configuré qui l'a (icône de l'objet)."""
        moves = self.api.by_id("moves")
        types: dict[int, int] = {}
        for vg, item_id, move_id in self.machine_rows:
            values = self._values_in(vg, moves[move_id], self._changelog[move_id])
            types.setdefault(item_id, int(values["type_id"]))
        return types

    def move_version_group_table(self) -> list[tuple]:
        moves = self.api.by_id("moves")
        changelog = self._changelog
        rows = []
        for vg in self.builder.vg_ids:
            effects = self.effects[vg]
            for move_id in sorted(self.moves_by_version_group[vg]):
                values = self._values_in(vg, moves[move_id], changelog[move_id])
                type_id = int(values["type_id"])
                effect = effects.get(move_id)
                if effect is None:
                    raise ValueError(f"Attaque {moves[move_id]['identifier']} absente des attaques pret du jeu {vg}")
                pret_move = self._pret_moves_by_id[vg][move_id]
                rows.append(
                    (
                        move_id,
                        vg,
                        type_id,
                        _game_power(optional_int(values["power"]), pret_move),
                        optional_int(values["accuracy"]),
                        # L'historique de PokéAPI oublie des changements (Repos, E-Coque) : le jeu fait foi.
                        pret_move.pp,
                        self._damage_class(vg, moves[move_id], type_id),
                        effect.description_fr,
                        effect.chance,
                    )
                )
        return rows

    @cached_property
    def _pret_moves_by_game(self) -> dict[str, GameMoves]:
        """Attaques lues dans pret, par identifiant de groupe de versions."""
        missing = [
            row["identifier"] for row in self.builder.vg_rows if row["identifier"] not in self.builder.pret_roots
        ]
        if missing:
            raise ValueError(f"Désassemblage pret manquant pour lire les attaques : {missing}")
        return {game.version_group: GameMoves(game.pret_format, self._pret_moves(game)) for game in self.builder.games}

    @cached_property
    def _pret_moves_by_id(self) -> dict[int, dict[int, PretMove]]:
        """Attaques lues dans pret, par groupe de versions (id) puis par attaque (id PokéAPI)."""
        return {
            int(row["id"]): {
                self.move_id(move.const.lower().replace("_", "-")): move
                for move in self._pret_moves_by_game[row["identifier"]].moves
            }
            for row in self.builder.vg_rows
        }

    @cached_property
    def effects(self) -> dict[int, dict[int, MoveEffect]]:
        """Effet de chaque attaque, par groupe de versions (id) puis par attaque (id PokéAPI), lu dans pret."""
        by_game = move_effects(self._pret_moves_by_game)
        return {
            int(row["id"]): {
                self.move_id(const.lower().replace("_", "-")): effect
                for const, effect in by_game[row["identifier"]].items()
            }
            for row in self.builder.vg_rows
        }

    def _pret_moves(self, game: Game) -> list[PretMove]:
        if game.pret_format is PretFormat.GEN3:
            return self.builder.gen3_repo(game, "les effets des attaques").moves
        return read_pret_moves(self.builder.pret_roots[game.version_group], game.pret_format)

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


def _game_power(api_power: int | None, pret_move: PretMove) -> int | None:
    """Puissance affichée : celle du jeu. Une attaque à dégâts fixes ou variables n'en affiche pas : PokéAPI la
    laisse vide (Sonicboom, Relâche) ou pret l'écrit 0 ou 1, valeur technique (Puissance Cachée)."""
    if api_power is None or pret_move.power <= 1:
        return None
    return pret_move.power
