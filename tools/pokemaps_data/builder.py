"""Construit les tables de pokedex.db à partir des CSV PokéAPI et des corrections de tools/data/.

`DatabaseBuilder` porte les référentiels communs (jeux, espèces, types, Pokédex) et coordonne
l'écriture ; chaque famille de tables vit dans son module `builder_<sujet>.py`.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from functools import cached_property
from pathlib import Path

from .builder_abilities import AbilityTables
from .builder_encounters import EncounterTables
from .builder_items import ItemTables
from .builder_maps import build_map_tables
from .builder_moves import MoveTables
from .builder_pokemon import PokemonTables
from .games import GAMES, Game, PretFormat
from .maps import GameMapData
from .pokeapi import PokeApi, optional_int, value_at
from .pret_gen2 import Gen2PretRepo

# Version du schéma : doit correspondre à la version de la base Room dans l'application.
SCHEMA_VERSION = 8

SCHEMA = Path(__file__).with_name("schema.sql")


class DatabaseBuilder:
    def __init__(
        self,
        api: PokeApi,
        games: tuple[Game, ...] = GAMES,
        map_data: dict[str, GameMapData] | None = None,
        pret_roots: dict[str, Path] | None = None,
    ) -> None:
        self.api = api
        self.games = games
        # Cartes générées par maps.build_maps, par groupe de versions (aucune si None).
        self.map_data = map_data or {}
        # Désassemblage pret de chaque groupe de versions (effets des attaques), aucun si None.
        self.pret_roots = pret_roots or {}
        self._gen2_repos: dict[str, Gen2PretRepo] = {}
        groups = {row["identifier"]: row for row in api.table("version_groups")}
        missing = [game.version_group for game in games if game.version_group not in groups]
        if missing:
            raise ValueError(f"Groupes de versions inconnus de PokéAPI : {missing}")
        self.vg_rows = [groups[game.version_group] for game in games]
        self.vg_ids = [int(row["id"]) for row in self.vg_rows]
        self.vg_order = {int(row["id"]): int(row["order"]) for row in api.table("version_groups")}
        self.vg_generation = {int(row["id"]): int(row["generation_id"]) for row in api.table("version_groups")}
        self.generations = sorted({self.vg_generation[vg] for vg in self.vg_ids})
        self.max_generation = max(self.generations)
        self.version_rows = [row for row in api.table("versions") if int(row["version_group_id"]) in self.vg_ids]
        self.version_ids = [int(row["id"]) for row in self.version_rows]
        # Familles de tables : elles lisent les référentiels ci-dessous et dépendent parfois l'une de l'autre
        # (les objets reprennent les CT et les objets d'évolution).
        self.pokemon = PokemonTables(self)
        self.moves = MoveTables(self)
        self.items = ItemTables(self)
        self.encounters = EncounterTables(self)
        self.abilities = AbilityTables(self)

    # --- Référentiels ---------------------------------------------------------

    def game_of(self, version_group_id: int) -> Game:
        """Jeu configuré du groupe de versions `version_group_id`."""
        for game, vg in zip(self.games, self.vg_ids, strict=True):
            if vg == version_group_id:
                return game
        raise ValueError(f"Groupe de versions non configuré : {version_group_id}")

    def gen2_repo(self, game: Game, purpose: str) -> Gen2PretRepo:
        """Désassemblage pret du jeu de la 2e génération `game`, lu une seule fois pour toutes les tables.

        `purpose` nomme ce qu'on y lit, pour le message d'erreur si le dépôt manque."""
        if game.pret_format is not PretFormat.GEN2:
            raise ValueError(f"{game.version_group} n'a pas de sources pret de la 2e génération ({purpose})")
        if game.version_group not in self.pret_roots:
            raise ValueError(f"Désassemblage pret manquant pour lire {purpose} : {game.version_group}")
        if game.version_group not in self._gen2_repos:
            self._gen2_repos[game.version_group] = Gen2PretRepo(self.pret_roots[game.version_group], game.pret_versions)
        return self._gen2_repos[game.version_group]

    @cached_property
    def species(self) -> dict[int, dict[str, str]]:
        """Espèces disponibles jusqu'à la génération la plus récente des jeux configurés."""
        return {
            int(row["id"]): row
            for row in self.api.table("pokemon_species")
            if int(row["generation_id"]) <= self.max_generation
        }

    @cached_property
    def default_pokemon(self) -> dict[int, int]:
        """Espèce -> identifiant de sa forme par défaut dans la table pokemon de PokéAPI."""
        return {
            int(row["species_id"]): int(row["id"])
            for row in self.api.table("pokemon")
            if row["is_default"] == "1" and int(row["species_id"]) in self.species
        }

    @cached_property
    def species_of_pokemon(self) -> dict[int, int]:
        return {pokemon_id: species_id for species_id, pokemon_id in self.default_pokemon.items()}

    @cached_property
    def type_rows(self) -> dict[int, dict[str, str]]:
        return {
            int(row["id"]): row
            for row in self.api.table("types")
            if int(row["id"]) < 1000 and int(row["generation_id"]) <= self.max_generation
        }

    def types_of_generation(self, generation: int) -> set[int]:
        return {type_id for type_id, row in self.type_rows.items() if int(row["generation_id"]) <= generation}

    # --- Tables simples ------------------------------------------------------

    def generation_table(self) -> list[tuple]:
        names = self.api.names("generation_names", "generation_id")
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])])
            for row in self.api.table("generations")
            if int(row["id"]) <= self.max_generation
        ]

    def region_table(self) -> list[tuple]:
        names = self.api.names("region_names", "region_id")
        regions = {row[3] for row in self.encounters.location_rows} | {row[3] for row in self.pokedex_table()}
        used = {region for region in regions if region is not None}
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])])
            for row in self.api.table("regions")
            if int(row["id"]) in used
        ]

    def version_group_table(self) -> list[tuple]:
        names = self.api.names("version_names", "version_id")
        rows = []
        for row in self.vg_rows:
            vg = int(row["id"])
            versions = [names[int(v["id"])] for v in self.version_rows if int(v["version_group_id"]) == vg]
            rows.append((vg, row["identifier"], " / ".join(versions), self.vg_generation[vg], self.vg_order[vg]))
        return rows

    def version_table(self) -> list[tuple]:
        names = self.api.names("version_names", "version_id")
        covers = {cover.version: cover for game in self.games for cover in game.covers}
        missing = [row["identifier"] for row in self.version_rows if row["identifier"] not in covers]
        if missing:
            raise ValueError(f"Jaquette manquante dans games.py pour les versions : {missing}")
        species = {row["identifier"]: species_id for species_id, row in self.species.items()}
        unknown = sorted({cover.mascot for cover in covers.values()} - species.keys())
        if unknown:
            raise ValueError(f"Pokémon de jaquette inconnus (games.py) : {unknown}")
        return [
            (
                int(row["id"]),
                row["identifier"],
                names[int(row["id"])],
                int(row["version_group_id"]),
                species[covers[row["identifier"]].mascot],
                covers[row["identifier"]].color,
            )
            for row in self.version_rows
        ]

    @cached_property
    def pokedex_links(self) -> list[tuple[int, int]]:
        return sorted(
            {
                (int(row["version_group_id"]), int(row["pokedex_id"]))
                for row in self.api.table("pokedex_version_groups")
                if int(row["version_group_id"]) in self.vg_ids
            }
        )

    def pokedex_table(self) -> list[tuple]:
        names = self.api.names("pokedex_prose", "pokedex_id")
        used = {pokedex for _, pokedex in self.pokedex_links}
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])], optional_int(row["region_id"]))
            for row in self.api.table("pokedexes")
            if int(row["id"]) in used
        ]

    def pokedex_entry_table(self) -> list[tuple]:
        used = {pokedex for _, pokedex in self.pokedex_links}
        return sorted(
            (int(row["pokedex_id"]), int(row["species_id"]), int(row["pokedex_number"]))
            for row in self.api.table("pokemon_dex_numbers")
            if int(row["pokedex_id"]) in used and int(row["species_id"]) in self.species
        )

    def type_table(self) -> list[tuple]:
        """Types des Pokémon et des attaques : ceux de type_rows, plus les types hors du tableau des types qu'une
        attaque des jeux configurés emploie (le type « ??? » de Malédiction en 2e génération)."""
        names = self.api.names("type_names", "type_id")
        types = self.api.by_id("types")
        rows = {**self.type_rows, **{type_id: types[type_id] for type_id in self.moves.types_outside_the_chart}}
        return [
            (type_id, row["identifier"], names[type_id], int(row["generation_id"]))
            for type_id, row in sorted(rows.items())
        ]

    def type_efficacy_table(self) -> list[tuple]:
        current = {
            (int(row["damage_type_id"]), int(row["target_type_id"])): int(row["damage_factor"])
            for row in self.api.table("type_efficacy")
        }
        # Valeur passée : « jusqu'à la génération N, le multiplicateur était X ».
        past: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for row in self.api.table("type_efficacy_past"):
            key = (int(row["damage_type_id"]), int(row["target_type_id"]))
            past[key].append((int(row["generation_id"]), int(row["damage_factor"])))
        rows = []
        for generation in self.generations:
            types = self.types_of_generation(generation)
            for attacking in sorted(types):
                for defending in sorted(types):
                    key = (attacking, defending)
                    factor = value_at(past.get(key, []), generation, current.get(key, 100))
                    rows.append((generation, attacking, defending, factor))
        return rows

    # --- Écriture -------------------------------------------------------------

    def tables(self, item_sprites: set[str]) -> dict[str, list[tuple]]:
        """Lignes de chaque table, dans l'ordre d'insertion imposé par les clés étrangères."""
        encounters, conditions = self.encounters.encounter_tables()
        descriptions = self.items.item_descriptions()
        items = [(*row, int(row[1] in item_sprites), descriptions.get(row[0])) for row in self.items.item_rows]
        return {
            "generation": self.generation_table(),
            "region": self.region_table(),
            "version_group": self.version_group_table(),
            "version": self.version_table(),
            "pokedex": self.pokedex_table(),
            "version_group_pokedex": self.pokedex_links,
            "pokedex_entry": self.pokedex_entry_table(),
            "type": self.type_table(),
            "type_efficacy": self.type_efficacy_table(),
            "stat": self.pokemon.stat_table(),
            "growth_rate": self.pokemon.growth_rate_table(),
            "pokemon": self.pokemon.pokemon_table(),
            "pokemon_type": self.pokemon.pokemon_type_table(),
            "pokemon_stat": self.pokemon.pokemon_stat_table(),
            "move": self.moves.move_table(),
            "move_version_group": self.moves.move_version_group_table(),
            "item": items,
            "machine": self.moves.machine_rows,
            "pokemon_move": self.moves.pokemon_move_rows,
            "pokemon_item": self.items.pokemon_item_rows,
            "egg_group": self.pokemon.egg_group_table(),
            "pokemon_egg_group": self.pokemon.egg_group_rows,
            "ability": self.abilities.ability_table(),
            "ability_version_group": self.abilities.ability_version_group_table(),
            "pokemon_ability": self.abilities.pokemon_ability_rows,
            "evolution": self.pokemon.evolution_rows,
            "location": self.encounters.location_rows,
            "location_area": self.encounters.location_area_table(),
            "encounter_method": self.encounters.encounter_method_table(),
            "encounter_condition_value": self.encounters.encounter_condition_value_table(),
            "encounter": encounters,
            "encounter_condition": conditions,
            "encounter_rate": self.encounters.encounter_rate_table(),
            **build_map_tables(self),
        }

    def write(self, output: Path, item_sprites: set[str]) -> None:
        tables = self.tables(item_sprites)
        output.parent.mkdir(parents=True, exist_ok=True)
        tmp = output.with_suffix(".tmp")
        tmp.unlink(missing_ok=True)
        connection = sqlite3.connect(tmp)
        try:
            connection.executescript(SCHEMA.read_text(encoding="utf-8"))
            for table, rows in tables.items():
                if not rows:
                    continue
                placeholders = ", ".join("?" * len(rows[0]))
                connection.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            connection.commit()
            connection.execute("VACUUM")
        finally:
            connection.close()
        tmp.replace(output)
