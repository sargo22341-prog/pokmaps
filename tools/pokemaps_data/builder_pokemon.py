"""Tables des Pokémon : fiches, types, statistiques et évolutions par génération."""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from .pokeapi import ENGLISH, FRENCH, clean_text, optional_int, value_at

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

# Stats affichées par génération : la 1re génération a une seule stat « Spécial » (id 9).
GEN1_STATS = (1, 2, 3, 6, 9)
MODERN_STATS = (1, 2, 3, 4, 5, 6)
STAT_NAME_FALLBACK = {9: "Spécial"}


class PokemonTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    def stat_table(self) -> list[tuple]:
        names = self.api.names("stat_names", "stat_id")
        used = set(GEN1_STATS if 1 in self.builder.generations else ()) | (
            set(MODERN_STATS) if self.builder.max_generation > 1 else set()
        )
        return [
            (int(row["id"]), row["identifier"], names.get(int(row["id"])) or STAT_NAME_FALLBACK[int(row["id"])])
            for row in self.api.table("stats")
            if int(row["id"]) in used
        ]

    def growth_rate_table(self) -> list[tuple]:
        names = self.api.names("growth_rate_prose", "growth_rate_id")
        return [(int(row["id"]), row["identifier"], names[int(row["id"])]) for row in self.api.table("growth_rates")]

    def pokemon_table(self) -> list[tuple]:
        names_fr = self.api.names("pokemon_species_names", "pokemon_species_id")
        genus_fr = self.api.names("pokemon_species_names", "pokemon_species_id", column="genus")
        names_en = self.api.names("pokemon_species_names", "pokemon_species_id", language=ENGLISH)
        sizes = {int(row["id"]): row for row in self.api.table("pokemon")}
        descriptions = self._descriptions()
        rows = []
        for species_id, row in sorted(self.builder.species.items()):
            size = sizes[self.builder.default_pokemon[species_id]]
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
        preferred = set(self.builder.version_ids)
        best: dict[int, tuple[tuple[int, int], str]] = {}
        for row in self.api.table("pokemon_species_flavor_text"):
            if int(row["language_id"]) != FRENCH:
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
        for generation in self.builder.generations:
            for species_id in self._species_of_generation(generation):
                pokemon_id = self.builder.default_pokemon[species_id]
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
        for generation in self.builder.generations:
            stats = GEN1_STATS if generation == 1 else MODERN_STATS
            for species_id in self._species_of_generation(generation):
                pokemon_id = self.builder.default_pokemon[species_id]
                for stat in stats:
                    value = value_at(past.get((pokemon_id, stat), []), generation, current.get((pokemon_id, stat)))
                    if value is None:
                        raise ValueError(
                            f"Stat {stat} manquante pour le Pokémon {species_id} (génération {generation})"
                        )
                    rows.append((species_id, generation, stat, value))
        return rows

    def _species_of_generation(self, generation: int) -> list[int]:
        """Espèces déjà apparues à `generation`, triées par numéro."""
        return [
            species_id
            for species_id, row in sorted(self.builder.species.items())
            if int(row["generation_id"]) <= generation
        ]

    @cached_property
    def evolution_rows(self) -> list[tuple]:
        triggers = {int(row["id"]): row["identifier"] for row in self.api.table("evolution_triggers")}
        by_target: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row in self.api.table("pokemon_evolution"):
            by_target[int(row["evolved_species_id"])].append(row)
        rows = []
        for vg in self.builder.vg_ids:
            for target, candidates in sorted(by_target.items()):
                source = self.builder.species.get(target, {}).get("evolves_from_species_id")
                if target not in self.builder.species or not source:
                    continue
                if int(self.builder.species[target]["generation_id"]) > self.builder.vg_generation[vg]:
                    continue
                rows += [
                    (vg, int(source), target, triggers[int(row["evolution_trigger_id"])], *_evolution_conditions(row))
                    for row in self._evolution_methods(vg, candidates)
                ]
        return [(index, *row) for index, row in enumerate(rows, start=1)]

    def _evolution_methods(self, vg: int, candidates: list[dict[str, str]]) -> list[dict[str, str]]:
        """Méthodes valables dans ce jeu : celles introduites au plus tard dans ce groupe de versions,
        en ne gardant que la plus récente (la méthode peut changer d'un jeu à l'autre)."""
        order = self.builder.vg_order
        valid = [row for row in candidates if order[int(row["version_group_id"])] <= order[vg]]
        if not valid:
            return []
        latest = max(order[int(row["version_group_id"])] for row in valid)
        return [row for row in valid if order[int(row["version_group_id"])] == latest]


def _evolution_conditions(row: dict[str, str]) -> tuple:
    return (
        optional_int(row["minimum_level"]),
        optional_int(row["trigger_item_id"]),
        optional_int(row["held_item_id"]),
        optional_int(row["minimum_happiness"]),
        row["time_of_day"] or None,
        optional_int(row["known_move_id"]),
        optional_int(row["trade_species_id"]),
    )
