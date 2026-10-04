"""Construit les tables de pokedex.db à partir des CSV PokéAPI et des corrections de tools/data/."""

from __future__ import annotations

import csv
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from .games import GAMES, ONE_OFF_METHODS, Game
from .maps import GameMapData, identifier
from .pokeapi import ENGLISH, PokeApi, clean_text, optional_int

# Version du schéma : doit correspondre à la version de la base Room dans l'application.
SCHEMA_VERSION = 3

SCHEMA = Path(__file__).with_name("schema.sql")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Stats affichées par génération : la 1re génération a une seule stat « Spécial » (id 9).
GEN1_STATS = (1, 2, 3, 6, 9)
MODERN_STATS = (1, 2, 3, 4, 5, 6)
STAT_NAME_FALLBACK = {9: "Spécial"}

# Catégories d'objets toujours incluses (en plus des objets d'évolution et des CT/CS).
BALL_CATEGORIES = ("standard-balls", "special-balls")

# Jusqu'à la 3e génération, la catégorie physique / spéciale d'une attaque dépend de son type.
LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION = 3
DAMAGE_CLASSES = {1: "status", 2: "physical", 3: "special"}


def _area_key(location_identifier: str, area_identifier: str) -> str:
    return f"{location_identifier}/{area_identifier}" if area_identifier else location_identifier


@dataclass
class EncounterGroup:
    version_id: int
    location_area_id: int
    pokemon_id: int
    method_id: int
    conditions: tuple[int, ...]
    min_level: int
    max_level: int
    chance: float | None
    quantity: int
    notes: list[str] = field(default_factory=list)


class DatabaseBuilder:
    def __init__(
        self, api: PokeApi, games: tuple[Game, ...] = GAMES, map_data: dict[str, GameMapData] | None = None
    ) -> None:
        self.api = api
        self.games = games
        # Cartes générées par maps.build_maps, par groupe de versions (aucune si None).
        self.map_data = map_data or {}
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

    # --- Référentiels ---------------------------------------------------------

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
        used = {loc_region for loc_region in self._used_regions if loc_region is not None}
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
            rows.append((vg, row["identifier"], " / ".join(versions), self.vg_generation[vg], self.vg_order[vg], 1))
        return rows

    def version_table(self) -> list[tuple]:
        names = self.api.names("version_names", "version_id")
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])], int(row["version_group_id"]))
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

    @cached_property
    def pokemon_by_version_group(self) -> dict[int, set[int]]:
        """Espèces présentes dans le Pokédex de chaque jeu (utilisé pour les sprites)."""
        by_pokedex: dict[int, set[int]] = defaultdict(set)
        for pokedex, species, _ in self.pokedex_entry_table():
            by_pokedex[pokedex].add(species)
        result: dict[int, set[int]] = defaultdict(set)
        for vg, pokedex in self.pokedex_links:
            result[vg] |= by_pokedex[pokedex]
        return result

    def type_table(self) -> list[tuple]:
        names = self.api.names("type_names", "type_id")
        return [
            (type_id, row["identifier"], names[type_id], int(row["generation_id"]))
            for type_id, row in sorted(self.type_rows.items())
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
                    factor = _value_at(past.get(key, []), generation, current.get(key, 100))
                    rows.append((generation, attacking, defending, factor))
        return rows

    def stat_table(self) -> list[tuple]:
        names = self.api.names("stat_names", "stat_id")
        used = set(GEN1_STATS if 1 in self.generations else ()) | (
            set(MODERN_STATS) if self.max_generation > 1 else set()
        )
        return [
            (int(row["id"]), row["identifier"], names.get(int(row["id"])) or STAT_NAME_FALLBACK[int(row["id"])])
            for row in self.api.table("stats")
            if int(row["id"]) in used
        ]

    def growth_rate_table(self) -> list[tuple]:
        names = self.api.names("growth_rate_prose", "growth_rate_id")
        return [(int(row["id"]), row["identifier"], names[int(row["id"])]) for row in self.api.table("growth_rates")]

    # --- Pokémon --------------------------------------------------------------

    def pokemon_table(self) -> list[tuple]:
        names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
        genus_fr = self.api.names("pokemon_species_names", "pokemon_species_id", column="genus")
        names_en = self.api.names("pokemon_species_names", "pokemon_species_id", language=ENGLISH)
        sizes = {int(row["id"]): row for row in self.api.table("pokemon")}
        descriptions = self._descriptions()
        rows = []
        for species_id, row in sorted(self.species.items()):
            size = sizes[self.default_pokemon[species_id]]
            rows.append(
                (
                    species_id,
                    row["identifier"],
                    names_fr[species_id],
                    names_en[species_id],
                    genus_fr[species_id],
                    int(row["generation_id"]),
                    optional_int(row["evolves_from_species_id"]),
                    int(row["evolution_chain_id"]),
                    int(row["capture_rate"]),
                    int(row["gender_rate"]),
                    int(row["growth_rate_id"]),
                    int(size["height"]),
                    int(size["weight"]),
                    int(row["is_legendary"]),
                    int(row["is_mythical"]),
                    int(row["is_baby"]),
                    descriptions.get(species_id),
                )
            )
        return rows

    def _descriptions(self) -> dict[int, str]:
        """Description française du Pokédex : celle d'un jeu configuré si elle existe, sinon la plus ancienne."""
        preferred = set(self.version_ids)
        best: dict[int, tuple[tuple[int, int], str]] = {}
        for row in self.api.table("pokemon_species_flavor_text"):
            if int(row["language_id"]) != 5:
                continue
            species_id, version = int(row["species_id"]), int(row["version_id"])
            rank = (0 if version in preferred else 1, version)
            if species_id not in best or rank < best[species_id][0]:
                best[species_id] = (rank, clean_text(row["flavor_text"]))
        return {species_id: text for species_id, (_, text) in best.items()}

    def pokemon_type_table(self) -> list[tuple]:
        current: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for row in self.api.table("pokemon_types"):
            current[int(row["pokemon_id"])].append((int(row["slot"]), int(row["type_id"])))
        past: dict[int, dict[int, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        for row in self.api.table("pokemon_types_past"):
            past[int(row["pokemon_id"])][int(row["generation_id"])].append((int(row["slot"]), int(row["type_id"])))
        rows = []
        for generation in self.generations:
            for species_id, row in sorted(self.species.items()):
                if int(row["generation_id"]) > generation:
                    continue
                pokemon_id = self.default_pokemon[species_id]
                types = current[pokemon_id]
                # Types passés : « jusqu'à la génération N, le Pokémon avait ces types ».
                for until in sorted(past[pokemon_id]):
                    if until >= generation:
                        types = past[pokemon_id][until]
                        break
                rows += [(species_id, generation, slot, type_id) for slot, type_id in sorted(types)]
        return rows

    def pokemon_stat_table(self) -> list[tuple]:
        current: dict[tuple[int, int], int] = {
            (int(row["pokemon_id"]), int(row["stat_id"])): int(row["base_stat"])
            for row in self.api.table("pokemon_stats")
        }
        past: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for row in self.api.table("pokemon_stats_past"):
            key = (int(row["pokemon_id"]), int(row["stat_id"]))
            past[key].append((int(row["generation_id"]), int(row["base_stat"])))
        rows = []
        for generation in self.generations:
            stats = GEN1_STATS if generation == 1 else MODERN_STATS
            for species_id, row in sorted(self.species.items()):
                if int(row["generation_id"]) > generation:
                    continue
                pokemon_id = self.default_pokemon[species_id]
                for stat in stats:
                    value = _value_at(past.get((pokemon_id, stat), []), generation, current.get((pokemon_id, stat)))
                    if value is None:
                        raise ValueError(
                            f"Stat {stat} manquante pour le Pokémon {species_id} (génération {generation})"
                        )
                    rows.append((species_id, generation, stat, value))
        return rows

    # --- Attaques -------------------------------------------------------------

    @cached_property
    def pokemon_move_rows(self) -> list[tuple]:
        methods = {int(row["id"]): row["identifier"] for row in self.api.table("pokemon_move_methods")}
        rows = set()
        for row in self.api.table("pokemon_moves"):
            vg = int(row["version_group_id"])
            pokemon_id = int(row["pokemon_id"])
            if vg not in self.vg_ids or pokemon_id not in self.species_of_pokemon:
                continue
            method = methods[int(row["pokemon_move_method_id"])]
            level = int(row["level"]) if method == "level-up" else 0
            rows.add((self.species_of_pokemon[pokemon_id], vg, int(row["move_id"]), method, level))
        return sorted(rows)

    @cached_property
    def machine_rows(self) -> list[tuple]:
        return sorted(
            (int(row["version_group_id"]), int(row["item_id"]), int(row["move_id"]))
            for row in self.api.table("machines")
            if int(row["version_group_id"]) in self.vg_ids
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
        for vg in self.vg_ids:
            order = self.vg_order[vg]
            generation = self.vg_generation[vg]
            for move_id in sorted(self.moves_by_version_group[vg]):
                move = moves[move_id]
                values = {name: move[name] for name in ("type_id", "power", "pp", "accuracy")}
                later = sorted(
                    (
                        row
                        for row in changelog[move_id]
                        if self.vg_order[int(row["changed_in_version_group_id"])] > order
                    ),
                    key=lambda row: self.vg_order[int(row["changed_in_version_group_id"])],
                    reverse=True,
                )
                # Du changement le plus récent au plus proche : la dernière valeur écrite est celle du jeu.
                for change in later:
                    for name in values:
                        if change[name]:
                            values[name] = change[name]
                type_id = int(values["type_id"])
                damage_class = DAMAGE_CLASSES[int(move["damage_class_id"])]
                if generation <= LAST_TYPE_BASED_DAMAGE_CLASS_GENERATION and damage_class != "status":
                    damage_class = DAMAGE_CLASSES[int(self.type_rows[type_id]["damage_class_id"])]
                rows.append(
                    (
                        move_id,
                        vg,
                        type_id,
                        optional_int(values["power"]),
                        optional_int(values["accuracy"]),
                        int(values["pp"]),
                        damage_class,
                    )
                )
        return rows

    # --- Évolutions et objets -------------------------------------------------

    @cached_property
    def evolution_rows(self) -> list[tuple]:
        triggers = {int(row["id"]): row["identifier"] for row in self.api.table("evolution_triggers")}
        by_target: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row in self.api.table("pokemon_evolution"):
            by_target[int(row["evolved_species_id"])].append(row)
        rows = []
        for vg in self.vg_ids:
            order = self.vg_order[vg]
            for target, candidates in sorted(by_target.items()):
                source = self.species.get(target, {}).get("evolves_from_species_id")
                if target not in self.species or not source:
                    continue
                if int(self.species[target]["generation_id"]) > self.vg_generation[vg]:
                    continue
                # Méthodes valables dans ce jeu : celles introduites au plus tard dans ce groupe de versions,
                # en ne gardant que la plus récente (la méthode peut changer d'un jeu à l'autre).
                valid = [row for row in candidates if self.vg_order[int(row["version_group_id"])] <= order]
                if not valid:
                    continue
                latest = max(self.vg_order[int(row["version_group_id"])] for row in valid)
                for row in valid:
                    if self.vg_order[int(row["version_group_id"])] != latest:
                        continue
                    rows.append(
                        (
                            vg,
                            int(source),
                            target,
                            triggers[int(row["evolution_trigger_id"])],
                            optional_int(row["minimum_level"]),
                            optional_int(row["trigger_item_id"]),
                            optional_int(row["held_item_id"]),
                            optional_int(row["minimum_happiness"]),
                            row["time_of_day"] or None,
                            optional_int(row["known_move_id"]),
                            optional_int(row["trade_species_id"]),
                        )
                    )
        return [(index, *row) for index, row in enumerate(rows, start=1)]

    @cached_property
    def item_rows(self) -> list[tuple[int, str, str, str]]:
        names = self.api.names("item_names", "item_id")
        items = self.api.by_id("items")
        categories = {int(row["id"]): row["identifier"] for row in self.api.table("item_categories")}
        used = {item for _, item, _ in self.machine_rows}
        used |= set(self._map_item_ids.values())
        for row in self.evolution_rows:
            used |= {item for item in (row[6], row[7]) if item}
        # Poké Balls existant dans au moins une des générations configurées.
        ball_ids = {item_id for item_id, row in items.items() if categories[int(row["category_id"])] in BALL_CATEGORIES}
        for row in self.api.table("item_game_indices"):
            if int(row["item_id"]) in ball_ids and int(row["generation_id"]) in self.generations:
                used.add(int(row["item_id"]))
        return [
            (item_id, items[item_id]["identifier"], names[item_id], categories[int(items[item_id]["category_id"])])
            for item_id in sorted(used)
        ]

    @cached_property
    def _map_item_ids(self) -> dict[str, int]:
        """Objets posés sur les cartes : identifiant PokéAPI -> id."""
        ids = {row["identifier"]: int(row["id"]) for row in self.api.table("items")}
        identifiers = {obj.item for data in self.map_data.values() for obj in data.objects if obj.item}
        unknown = sorted(identifiers - ids.keys())
        if unknown:
            raise ValueError(f"Objets des cartes inconnus de PokéAPI : {unknown} (voir maps.ITEM_ALIASES)")
        return {identifier: ids[identifier] for identifier in identifiers}

    # --- Lieux et rencontres --------------------------------------------------

    @cached_property
    def raw_encounters(self) -> list[dict[str, str]]:
        return [row for row in self.api.table("encounters") if int(row["version_id"]) in self.version_ids]

    @cached_property
    def used_areas(self) -> set[int]:
        return {int(row["location_area_id"]) for row in self.raw_encounters}

    @cached_property
    def name_fixes(self) -> dict[tuple[str, str], str]:
        with (DATA_DIR / "name_fixes.csv").open(encoding="utf-8", newline="") as handle:
            return {(row["kind"], row["key"]): row["name_fr"] for row in csv.DictReader(handle)}

    @cached_property
    def area_keys(self) -> dict[int, str]:
        """Zone -> clé lisible `lieu/zone` utilisée par les fichiers de tools/data/."""
        locations = self.api.by_id("locations")
        return {
            int(row["id"]): _area_key(locations[int(row["location_id"])]["identifier"], row["identifier"])
            for row in self.api.table("location_areas")
        }

    def location_area_table(self) -> list[tuple]:
        names = self.api.names("location_area_prose", "location_area_id")
        areas = self.api.by_id("location_areas")
        locations = self.api.by_id("locations")
        location_names = self.api.names("location_names", "location_id")
        rows = []
        for area_id in sorted(self.used_areas):
            area = areas[area_id]
            location = locations[int(area["location_id"])]
            name = self.name_fixes.get(("area", self.area_keys[area_id])) or names.get(area_id)
            if not name:
                base = location_names.get(int(location["id"]), location["identifier"])
                name = f"{base} ({area['identifier']})" if area["identifier"] else base
            rows.append((area_id, int(area["location_id"]), area["identifier"], name))
        return rows

    def location_table(self) -> list[tuple]:
        names = self.api.names("location_names", "location_id")
        locations = self.api.by_id("locations")
        areas = self.api.by_id("location_areas")
        used = sorted({int(areas[area]["location_id"]) for area in self.used_areas})
        rows = []
        for location_id in used:
            row = locations[location_id]
            name = self.name_fixes.get(("location", row["identifier"])) or names.get(location_id)
            if not name:
                raise ValueError(f"Nom français manquant pour le lieu {row['identifier']} (tools/data/name_fixes.csv)")
            rows.append((location_id, row["identifier"], name, optional_int(row["region_id"])))
        return rows

    @cached_property
    def _used_regions(self) -> set[int | None]:
        regions = {row[3] for row in self.location_table()}
        regions |= {row[3] for row in self.pokedex_table()}
        return regions

    @cached_property
    def encounter_groups(self) -> list[EncounterGroup]:
        slots = self.api.by_id("encounter_slots")
        methods = self.api.by_id("encounter_methods")
        default_conditions = {
            int(row["id"]) for row in self.api.table("encounter_condition_values") if row["is_default"] == "1"
        }
        conditions: dict[int, set[int]] = defaultdict(set)
        for row in self.api.table("encounter_condition_value_map"):
            value = int(row["encounter_condition_value_id"])
            if value not in default_conditions:
                conditions[int(row["encounter_id"])].add(value)

        groups: dict[tuple, EncounterGroup] = {}
        for row in self.raw_encounters:
            slot = slots[int(row["encounter_slot_id"])]
            method_id = int(slot["encounter_method_id"])
            one_off = methods[method_id]["identifier"] in ONE_OFF_METHODS
            key = (
                int(row["version_id"]),
                int(row["location_area_id"]),
                int(row["pokemon_id"]),
                method_id,
                tuple(sorted(conditions[int(row["id"])])),
            )
            species = self.species_of_pokemon[int(row["pokemon_id"])]
            low, high = int(row["min_level"]), int(row["max_level"])
            group = groups.get(key)
            if group is None:
                groups[key] = EncounterGroup(
                    key[0], key[1], species, method_id, key[4], low, high, None if one_off else 0.0, 0
                )
                group = groups[key]
            group.min_level = min(group.min_level, low)
            group.max_level = max(group.max_level, high)
            if one_off:
                group.quantity += 1
            else:
                group.chance += int(slot["rarity"])
                group.quantity = 1
        return self._apply_curation(list(groups.values()))

    def _apply_curation(self, groups: list[EncounterGroup]) -> list[EncounterGroup]:
        versions = {row["identifier"]: int(row["id"]) for row in self.api.table("versions")}
        species = {row["identifier"]: int(row["id"]) for row in self.api.table("pokemon_species")}
        methods = {row["identifier"]: int(row["id"]) for row in self.api.table("encounter_methods")}
        areas = {key: area_id for area_id, key in self.area_keys.items()}
        names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
        excluded: set[int] = set()
        with (DATA_DIR / "encounter_curation.csv").open(encoding="utf-8", newline="") as handle:
            for line, row in enumerate(csv.DictReader(handle), start=2):
                matched = False
                for version in row["versions"].split("|"):
                    if versions[version] not in self.version_ids:
                        continue
                    for index, group in enumerate(groups):
                        if (
                            group.version_id == versions[version]
                            and group.location_area_id == areas[row["location_area"]]
                            and group.pokemon_id == species[row["pokemon"]]
                            and group.method_id == methods[row["method"]]
                        ):
                            matched = True
                            if row["action"] == "exclude":
                                excluded.add(index)
                            elif row["action"] == "note":
                                group.notes.append(row["value"])
                            elif row["action"] == "trade_for":
                                group.notes.append(f"Échange contre {names_fr[species[row['value']]]}")
                            else:
                                raise ValueError(f"encounter_curation.csv:{line} : action inconnue {row['action']}")
                if not matched and any(versions[v] in self.version_ids for v in row["versions"].split("|")):
                    raise ValueError(f"encounter_curation.csv:{line} ne correspond à aucune rencontre : {row}")
        return [group for index, group in enumerate(groups) if index not in excluded]

    @cached_property
    def method_rank(self) -> dict[int, int]:
        return {int(row["id"]): int(row["order"]) for row in self.api.table("encounter_methods")}

    def encounter_tables(self) -> tuple[list[tuple], list[tuple]]:
        groups = sorted(
            self.encounter_groups,
            key=lambda g: (
                g.version_id,
                g.location_area_id,
                self.method_rank[g.method_id],
                g.conditions,
                -(g.chance or 0),
                g.pokemon_id,
            ),
        )
        encounters, conditions = [], []
        for index, group in enumerate(groups, start=1):
            encounters.append(
                (
                    index,
                    group.version_id,
                    group.location_area_id,
                    group.pokemon_id,
                    group.method_id,
                    group.min_level,
                    group.max_level,
                    group.chance,
                    group.quantity,
                    " ; ".join(group.notes) or None,
                )
            )
            conditions += [(index, value) for value in group.conditions]
        return encounters, conditions

    def encounter_method_table(self) -> list[tuple]:
        names = self.api.names("encounter_method_prose", "encounter_method_id")
        used = {group.method_id for group in self.encounter_groups}
        return [
            (
                int(row["id"]),
                row["identifier"],
                names[int(row["id"])],
                int(row["order"]),
                int(row["identifier"] in ONE_OFF_METHODS),
            )
            for row in self.api.table("encounter_methods")
            if int(row["id"]) in used
        ]

    def encounter_condition_value_table(self) -> list[tuple]:
        names = self.api.names("encounter_condition_value_prose", "encounter_condition_value_id")
        used = {value for group in self.encounter_groups for value in group.conditions}
        return [
            (int(row["id"]), row["identifier"], names[int(row["id"])])
            for row in self.api.table("encounter_condition_values")
            if int(row["id"]) in used
        ]

    def encounter_rate_table(self) -> list[tuple]:
        return sorted(
            (int(row["version_id"]), int(row["location_area_id"]), int(row["encounter_method_id"]), int(row["rate"]))
            for row in self.api.table("location_area_encounter_rates")
            if int(row["version_id"]) in self.version_ids and int(row["location_area_id"]) in self.used_areas
        )

    # --- Cartes ---------------------------------------------------------------

    def map_tables(self) -> dict[str, list[tuple]]:
        vg_ids = {row["identifier"]: int(row["id"]) for row in self.vg_rows}
        area_ids = {key: area_id for area_id, key in self.area_keys.items()}
        species = {row["identifier"]: int(row["id"]) for row in self.species.values()}
        known_areas = {row[0] for row in self.location_area_table()}
        maps, areas, warps, objects = [], [], [], []
        for version_group, data in self.map_data.items():
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
                if obj.pokemon and obj.pokemon not in species:
                    raise ValueError(f"Pokémon des cartes inconnu de PokéAPI : {obj.pokemon}")
                objects.append(
                    (
                        len(objects) + 1,
                        ids[obj.map_const],
                        obj.kind,
                        obj.x,
                        obj.y,
                        obj.sprite,
                        obj.item and self._map_item_ids[obj.item],
                        obj.pokemon and species[obj.pokemon],
                        obj.level,
                        obj.trainer_class,
                    )
                )
        return {"map": maps, "map_area": sorted(set(areas)), "map_warp": warps, "map_object": objects}

    # --- Écriture -------------------------------------------------------------

    def write(self, output: Path, item_sprites: set[str]) -> None:
        encounters, conditions = self.encounter_tables()
        tables = {
            "generation": self.generation_table(),
            "region": self.region_table(),
            "version_group": self.version_group_table(),
            "version": self.version_table(),
            "pokedex": self.pokedex_table(),
            "version_group_pokedex": self.pokedex_links,
            "pokedex_entry": self.pokedex_entry_table(),
            "type": self.type_table(),
            "type_efficacy": self.type_efficacy_table(),
            "stat": self.stat_table(),
            "growth_rate": self.growth_rate_table(),
            "pokemon": self.pokemon_table(),
            "pokemon_type": self.pokemon_type_table(),
            "pokemon_stat": self.pokemon_stat_table(),
            "move": self.move_table(),
            "move_version_group": self.move_version_group_table(),
            "item": [(*row, int(row[1] in item_sprites)) for row in self.item_rows],
            "machine": self.machine_rows,
            "pokemon_move": self.pokemon_move_rows,
            "evolution": self.evolution_rows,
            "location": self.location_table(),
            "location_area": self.location_area_table(),
            "encounter_method": self.encounter_method_table(),
            "encounter_condition_value": self.encounter_condition_value_table(),
            "encounter": encounters,
            "encounter_condition": conditions,
            "encounter_rate": self.encounter_rate_table(),
            **self.map_tables(),
        }
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


def _value_at(past: list[tuple[int, int]], generation: int, current: int | None) -> int | None:
    """Valeur pour `generation` à partir d'un historique « jusqu'à la génération N : valeur »."""
    for until, value in sorted(past):
        if until >= generation:
            return value
    return current
