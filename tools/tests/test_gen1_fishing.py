"""Pêche de Rouge, Bleu et Jaune absente de PokéAPI (pret_fishing.py, builder_fishing_gen1.py)."""

import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.pret_fishing import FishingSlot, read_fishing
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).parents[1] / ".cache"


def _rods(db: sqlite3.Connection, version: str, location: str, area: str) -> dict[str, set[tuple[str, int, float]]]:
    rows = db.execute(
        """SELECT em.identifier, p.identifier, e.min_level, e.chance FROM encounter e
           JOIN encounter_method em ON em.id = e.method_id JOIN pokemon p ON p.id = e.pokemon_id
           JOIN version v ON v.id = e.version_id JOIN location_area la ON la.id = e.location_area_id
           JOIN location l ON l.id = la.location_id
           WHERE v.identifier = ? AND l.identifier = ? AND la.identifier = ? AND em.identifier LIKE '%-rod'""",
        (version, location, area),
    ).fetchall()
    result: dict[str, set[tuple[str, int, float]]] = {}
    for method, pokemon, level, chance in rows:
        result.setdefault(method, set()).add((pokemon, level, chance))
    return result


def test_cerulean_gym_and_loreleis_room_have_fishing(db: sqlite3.Connection) -> None:
    old = {("magikarp", 5, 100.0)}
    good = {("goldeen", 10, 50.0), ("poliwag", 10, 50.0)}
    assert _rods(db, "red", "cerulean-city", "gym") == {
        "old-rod": old,
        "good-rod": good,
        "super-rod": {("psyduck", 15, 34.0), ("goldeen", 15, 33.0), ("krabby", 15, 33.0)},
    }
    # Jaune n'a pas l'Arène dans sa table de Méga Canne.
    assert _rods(db, "yellow", "cerulean-city", "gym") == {"old-rod": old, "good-rod": good}
    for version in ("red", "blue", "yellow"):
        assert _rods(db, version, "indigo-plateau", "loreleis-room") == {"old-rod": old, "good-rod": good}


def test_yellow_vermilion_dock_has_every_rod(db: sqlite3.Connection) -> None:
    rods = _rods(db, "yellow", "vermilion-city", "ss-anne-dock")
    assert rods.keys() == {"old-rod", "good-rod", "super-rod"}
    assert rods["old-rod"] == {("magikarp", 5, 100.0)}


@pytest.mark.pipeline
def test_rod_tables_are_read_from_pret() -> None:
    red = read_fishing(pret_dir(CACHE, "pokered"))
    yellow = read_fishing(pret_dir(CACHE, "pokeyellow"))
    assert red.old_rod == yellow.old_rod == (FishingSlot("MAGIKARP", 5, 100),)
    assert red.super_rod["CERULEAN_GYM"] == red.super_rod["CERULEAN_CITY"]
    assert "CERULEAN_GYM" not in yellow.super_rod
    # Seuils $66, $B2 et $E5 sur 256 de GenerateRandomFishingEncounter.
    assert [slot.chance for slot in yellow.super_rod["VERMILION_DOCK"]] == [40, 30, 20, 10]
