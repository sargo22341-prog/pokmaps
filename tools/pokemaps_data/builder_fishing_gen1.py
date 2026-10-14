"""Pêche de Rouge, Bleu et Jaune absente de PokéAPI, lue dans pret (pret_fishing.py).

PokéAPI oublie quelques cartes où l'on pêche depuis la terre ferme (en 1re génération, on ne pêche pas en surfant) :
tools/data/fishing_gen1.csv les nomme, relues dans les cartes du jeu. Chaque canne qui n'a aucune rencontre PokéAPI
dans la zone de la carte (map_areas.csv) reçoit celles du jeu ; une ligne qui n'ajoute rien arrête la génération.
"""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from .builder_wild_gen2 import EncounterIds, WildEncounter, displayed_map_areas, single_area
from .pret_fishing import FishingSlot, read_fishing
from .pret_identifiers import species_identifier
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .games import Game

_CSV = "fishing_gen1.csv"


def gen1_fishing_encounters(builder: DatabaseBuilder, game: Game, pokeapi: list[WildEncounter]) -> list[WildEncounter]:
    """Rencontres de pêche que PokéAPI n'a pas pour les cartes de fishing_gen1.csv, version par version."""
    fishing = read_fishing(builder.pret_root(game, "la pêche"))
    areas = displayed_map_areas(builder, game)
    ids = EncounterIds(builder)
    present = {(encounter.version_id, encounter.area_id, encounter.method_id) for encounter in pokeapi}
    result: list[WildEncounter] = []
    for const in _fishing_maps():
        if const not in areas:
            raise ValueError(f"{_CSV} : carte sans zone dans map_areas.csv : {const}")
        area_id = single_area(const, areas[const])
        rods = {
            "old-rod": fishing.old_rod,
            "good-rod": fishing.good_rod,
            "super-rod": fishing.super_rod.get(const, ()),
        }
        for version, _ in game.pret_versions:
            version_id = ids.versions[version]
            for method, slots in rods.items():
                if (version_id, area_id, ids.methods[method]) not in present:
                    result += [_encounter(ids, version_id, area_id, method, slot) for slot in slots]
    return result


def check_fishing_rows(builder: DatabaseBuilder, games: list[Game], added: list[WildEncounter]) -> None:
    """Une carte de fishing_gen1.csv qui n'ajoute rien à aucun jeu est une correction devenue inutile."""
    used = {encounter.area_id for encounter in added}
    for const in _fishing_maps():
        areas = {area for game in games for area in displayed_map_areas(builder, game).get(const, [])}
        if not areas & used:
            raise ValueError(f"{_CSV} : {const} a déjà toute sa pêche dans PokéAPI")


def _encounter(ids: EncounterIds, version_id: int, area_id: int, method: str, slot: FishingSlot) -> WildEncounter:
    species = ids.species[species_identifier(slot.species)]
    return WildEncounter(version_id, area_id, species, ids.methods[method], (), slot.level, slot.level, slot.chance)


def _fishing_maps() -> list[str]:
    with (DATA_DIR / _CSV).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    maps = [row.get("map", "") for row in rows]
    for line, row in enumerate(rows, start=2):
        if not row.get("map") or not (row.get("reason") or "").strip() or maps.count(row["map"]) > 1:
            raise ValueError(f"{_CSV}:{line} : carte manquante, répétée ou sans raison : {row}")
    return maps
