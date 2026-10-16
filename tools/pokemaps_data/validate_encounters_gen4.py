"""Probabilités des rencontres aléatoires de la 4e génération : 100 % pour chaque combinaison de conditions.

Le moteur DS remplace des emplacements isolés (heure, essaim, Pokéradar, cartouche GBA, Pokémon du jour) : une
condition ne couvre que les emplacements qu'elle remplace. Les valeurs d'une même condition s'excluent (matin, jour
ou nuit) ; une combinaison choisit une valeur par condition présente dans la table, et les rencontres retenues sont
celles dont toutes les conditions appartiennent à la combinaison. Chaque combinaison doit totaliser 100 %.
"""

from __future__ import annotations

import itertools
import sqlite3
from collections import defaultdict
from collections.abc import Iterable

# Préfixes des valeurs qui s'excluent ; toute autre valeur est une condition à elle seule.
_EXCLUSIVE_PREFIXES = ("time-", "swarm-", "radar-", "slot2-", "backlot-", "honey-tree-group-", "great-marsh-daily-")
_NATIONAL_DEX = frozenset({"story-progress-national-dex", "story-progress-before-national-dex"})
# Une table DS compte au plus cinq conditions (heure, essaim, radar, cartouche, Pokédex) : au plus 3×2×2×6×2.
_MAX_COMBINATIONS = 512
_GENERATION = 4

Row = tuple[float, frozenset[str]]


def condition_axis(identifier: str) -> str:
    """Condition PokéAPI dont `identifier` est une valeur."""
    if identifier in _NATIONAL_DEX:
        return "national-dex"
    return next((prefix for prefix in _EXCLUSIVE_PREFIXES if identifier.startswith(prefix)), identifier)


def condition_combinations(condition_sets: Iterable[frozenset[str]]) -> list[frozenset[str]] | None:
    """Chaque combinaison d'une valeur par condition présente ; None au-delà de _MAX_COMBINATIONS."""
    axes: dict[str, set[str]] = defaultdict(set)
    for conditions in condition_sets:
        for value in conditions:
            axes[condition_axis(value)].add(value)
    choices = [sorted(values) for _, values in sorted(axes.items())]
    count = 1
    for values in choices:
        count *= len(values)
    if count > _MAX_COMBINATIONS:
        return None
    return [frozenset(combination) for combination in itertools.product(*choices)]


def check_slot_probabilities(connection: sqlite3.Connection) -> list[str]:
    tables: dict[tuple[int, int, int], list[Row]] = defaultdict(list)
    query = """SELECT e.version_id, e.location_area_id, e.method_id, e.chance,
                      (SELECT group_concat(cv.identifier, '|') FROM encounter_condition c
                       JOIN encounter_condition_value cv ON cv.id = c.condition_value_id WHERE c.encounter_id = e.id)
               FROM encounter e JOIN encounter_method m ON m.id = e.method_id
               JOIN version v ON v.id = e.version_id JOIN version_group vg ON vg.id = v.version_group_id
               WHERE m.is_one_off = 0 AND vg.generation_id = ?"""
    for version, area, method, chance, conditions in connection.execute(query, (_GENERATION,)):
        tables[(version, area, method)].append(
            (chance, frozenset(conditions.split("|")) if conditions else frozenset())
        )
    errors = []
    for key, rows in sorted(tables.items()):
        if wrong := wrong_combinations(rows):
            errors.append(f"probabilités DS différentes de 100 % (version, zone, méthode) {key} : {wrong[:3]}")
    return errors


def wrong_combinations(rows: list[Row]) -> list[tuple[tuple[str, ...], float]]:
    """Combinaisons de conditions dont le total des rencontres retenues diffère de 100 %."""
    combinations = condition_combinations(conditions for _, conditions in rows)
    if combinations is None:
        return [(("trop de combinaisons",), 0.0)]
    wrong = []
    for selected in combinations:
        total = sum(chance for chance, conditions in rows if conditions <= selected)
        if abs(total - 100) > 0.01:
            wrong.append((tuple(sorted(selected)), total))
    return wrong
