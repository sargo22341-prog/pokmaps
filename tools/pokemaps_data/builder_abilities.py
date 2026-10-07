"""Tables des talents : noms, descriptions par jeu et talents de chaque Pokémon par génération.

Les talents apparaissent en 3e génération : pour des jeux plus anciens, ces tables restent vides.
"""

from __future__ import annotations

from collections import defaultdict
from functools import cached_property
from typing import TYPE_CHECKING

from .pokeapi import FRENCH, clean_text, optional_int

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

ABILITY_GENERATION = 3
# Les talents cachés apparaissent en 5e génération (PokéAPI n'en date pas toujours l'absence avant).
HIDDEN_ABILITY_GENERATION = 5

# Talent d'un emplacement (1, 2 ou 3 pour le talent caché) : (id du talent ou None, caché).
_Slot = tuple[int | None, bool]


class AbilityTables:
    def __init__(self, builder: DatabaseBuilder) -> None:
        self.builder = builder
        self.api = builder.api

    @cached_property
    def pokemon_ability_rows(self) -> list[tuple[int, int, int, int, int]]:
        """(espèce, génération, emplacement, talent, caché) pour chaque génération configurée qui a des talents."""
        current: dict[int, dict[int, _Slot]] = defaultdict(dict)
        for row in self.api.table("pokemon_abilities"):
            current[int(row["pokemon_id"])][int(row["slot"])] = (int(row["ability_id"]), row["is_hidden"] == "1")
        # Talents passés : « jusqu'à la génération N, cet emplacement avait ce talent (ou aucun) ».
        past: dict[int, dict[int, list[tuple[int, _Slot]]]] = defaultdict(lambda: defaultdict(list))
        for row in self.api.table("pokemon_abilities_past"):
            slot = (optional_int(row["ability_id"]), row["is_hidden"] == "1")
            past[int(row["pokemon_id"])][int(row["slot"])].append((int(row["generation_id"]), slot))
        abilities = self.api.by_id("abilities")
        rows = []
        for generation in (g for g in self.builder.generations if g >= ABILITY_GENERATION):
            for species_id, row in sorted(self.builder.species.items()):
                if int(row["generation_id"]) > generation:
                    continue
                pokemon_id = self.builder.default_pokemon[species_id]
                for slot in sorted(current[pokemon_id].keys() | past[pokemon_id].keys()):
                    ability, hidden = _slot_at(past[pokemon_id][slot], generation, current[pokemon_id].get(slot))
                    if ability is None or (hidden and generation < HIDDEN_ABILITY_GENERATION):
                        continue
                    if int(abilities[ability]["generation_id"]) > generation:
                        raise ValueError(
                            f"Talent {ability} du Pokémon {species_id} absent de la génération {generation}"
                        )
                    rows.append((species_id, generation, slot, ability, int(hidden)))
        return rows

    def ability_table(self) -> list[tuple]:
        names = self.api.names("ability_names", "ability_id")
        abilities = self.api.by_id("abilities")
        used = sorted({row[3] for row in self.pokemon_ability_rows})
        missing = [ability for ability in used if ability not in names]
        if missing:
            raise ValueError(f"Talents sans nom français dans PokéAPI : {missing}")
        return [
            (ability, abilities[ability]["identifier"], names[ability], int(abilities[ability]["generation_id"]))
            for ability in used
        ]

    def ability_version_group_table(self) -> list[tuple]:
        """Description française de chaque talent dans chaque jeu qui a des talents : celle du jeu, sinon celle
        du jeu précédent le plus proche qui en a une, sinon NULL."""
        order = self.builder.vg_order
        texts: dict[int, list[tuple[int, str]]] = defaultdict(list)
        for row in self.api.table("ability_flavor_text"):
            if int(row["language_id"]) == FRENCH:
                vg = int(row["version_group_id"])
                texts[int(row["ability_id"])].append((order[vg], clean_text(row["flavor_text"])))
        rows = []
        abilities = self.api.by_id("abilities")
        used = sorted({row[3] for row in self.pokemon_ability_rows})
        for vg in self.builder.vg_ids:
            generation = self.builder.vg_generation[vg]
            for ability in (a for a in used if int(abilities[a]["generation_id"]) <= generation):
                earlier = [(rank, text) for rank, text in texts[ability] if rank <= order[vg]]
                rows.append((ability, vg, max(earlier)[1] if earlier else None))
        return rows


def _slot_at(past: list[tuple[int, _Slot]], generation: int, current: _Slot | None) -> _Slot:
    for until, slot in sorted(past):
        if until >= generation:
            return slot
    return current or (None, False)
