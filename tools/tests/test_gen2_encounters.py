"""Rencontres, terrains et emplacements d'Or et d'Argent (phase 4 de plan_gen_2.md), dans l'aperçu de tous les jeux."""

import shutil
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.builder_wild_gen2 import _single_area
from pokemaps_data.games import GOLD_SILVER
from pokemaps_data.maps_terrain import wild_cells
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.pret_gen2_wild import has_water, special_battles, wild_tables
from pokemaps_data.validate import validate

GOLD_SILVER_GROUP = 3

# Rencontres : (version, zone « lieu/zone », Pokémon, méthode) -> (niveaux, probabilité, conditions, note).
_ENCOUNTERS = """
    SELECT v.identifier, l.identifier || CASE WHEN la.identifier = '' THEN '' ELSE '/' || la.identifier END,
           p.identifier, m.identifier, e.min_level, e.max_level, e.chance, e.note_fr,
           (SELECT group_concat(cv.identifier, '|') FROM encounter_condition ec
            JOIN encounter_condition_value cv ON cv.id = ec.condition_value_id WHERE ec.encounter_id = e.id)
    FROM encounter e JOIN version v ON v.id = e.version_id
    JOIN location_area la ON la.id = e.location_area_id JOIN location l ON l.id = la.location_id
    JOIN pokemon p ON p.id = e.pokemon_id JOIN encounter_method m ON m.id = e.method_id
"""


def _encounters(db: sqlite3.Connection, where: str, *args: str) -> set[tuple]:
    return set(db.execute(f"{_ENCOUNTERS} WHERE {where}", args).fetchall())


def test_preview_with_gold_and_silver_is_valid(preview_database: Path) -> None:
    assert validate(preview_database) == []


def test_random_encounters_total_100_for_each_time_of_day(preview_db: sqlite3.Connection) -> None:
    totals = preview_db.execute(
        """SELECT e.version_id, e.location_area_id, e.method_id, c.conditions, sum(e.chance) FROM encounter e
           JOIN version v ON v.id = e.version_id JOIN encounter_method m ON m.id = e.method_id
           LEFT JOIN (SELECT encounter_id, group_concat(condition_value_id) AS conditions FROM encounter_condition
                      GROUP BY encounter_id) c ON c.encounter_id = e.id
           WHERE v.version_group_id = ? AND m.is_one_off = 0
           GROUP BY e.version_id, e.location_area_id, e.method_id, c.conditions""",
        (GOLD_SILVER_GROUP,),
    ).fetchall()
    assert totals
    assert all(abs(total - 100) < 0.01 for *_, total in totals)
    # Les trois moments de la journée ont chacun leur table : « time-day », valeur par défaut de PokéAPI, est gardée.
    route_29 = _encounters(
        preview_db, "v.identifier = 'gold' AND l.identifier = 'johto-route-29' AND m.identifier = 'walk'"
    )
    assert {row[8] for row in route_29} == {"time-morning", "time-day", "time-night"}


def test_a_pokemon_only_at_night(preview_db: sqlite3.Connection) -> None:
    hoothoot = _encounters(
        preview_db, "v.version_group_id = 3 AND p.identifier = 'hoothoot' AND l.identifier = 'johto-route-29'"
    )
    assert {(row[0], row[3], row[6], row[8]) for row in hoothoot} == {
        ("gold", "walk", 85.0, "time-night"),
        ("silver", "walk", 85.0, "time-night"),
    }
    names = dict(preview_db.execute("SELECT identifier, name_fr FROM encounter_condition_value"))
    assert (names["time-night"], names["swarm-yes"]) == ("La nuit", "Pendant un essaim")


def test_headbutt_on_route_29(preview_db: sqlite3.Connection) -> None:
    headbutt = _encounters(
        preview_db, "v.identifier = 'gold' AND l.identifier = 'johto-route-29' AND m.identifier LIKE 'headbutt%'"
    )
    # Arbres ordinaires (table commune) et arbres rares (TreeMonSet_Canyon).
    assert {(row[2], row[3], row[6]) for row in headbutt} == {
        ("spearow", "headbutt", 80.0),
        ("aipom", "headbutt", 20.0),
        ("spearow", "headbutt-high", 50.0),
        ("heracross", "headbutt-high", 30.0),
        ("aipom", "headbutt-high", 20.0),
    }
    spots = preview_db.execute(
        """SELECT count(*) FROM map_spot s JOIN map m ON m.id = s.map_id
           WHERE m.identifier = 'route-29' AND m.version_group_id = ? AND s.kind = 'tree'""",
        (GOLD_SILVER_GROUP,),
    ).fetchone()[0]
    assert spots > 0


def test_headbutt_and_rock_smash_need_their_terrain(preview_db: sqlite3.Connection) -> None:
    # TreeMonMaps cite les Routes 45 et 46, RockMonMaps le Puits Ramoloss : aucun arbre ni rocher n'y permet ces
    # rencontres. Les rochers d'Irisia, eux, en donnent.
    routes = "l.identifier IN ('johto-route-45', 'johto-route-46')"
    assert not _encounters(preview_db, f"{routes} AND m.identifier LIKE 'headbutt%'")
    assert not _encounters(preview_db, "l.identifier = 'slowpoke-well' AND m.identifier = 'rock-smash'")
    rock = _encounters(
        preview_db, "v.identifier = 'gold' AND l.identifier = 'cianwood-city' AND m.identifier = 'rock-smash'"
    )
    assert {(row[2], row[6]) for row in rock} == {("krabby", 90.0), ("shuckle", 10.0)}


def test_fishing_comes_from_the_game(preview_db: sqlite3.Connection) -> None:
    # PokéAPI perd les moments de la journée de la Méga Canne d'Argent : Stari ne mord que la nuit.
    super_rod = _encounters(
        preview_db, "v.identifier = 'silver' AND l.identifier = 'cherrygrove-city' AND m.identifier = 'super-rod'"
    )
    assert {(row[2], row[6], row[8]) for row in super_rod if row[2] in ("corsola", "staryu")} == {
        ("corsola", 30.0, "time-morning"),
        ("corsola", 30.0, "time-day"),
        ("staryu", 30.0, "time-night"),
    }
    # Pendant l'essaim de Qwilfish, la Super Canne garde son Magicarpe (absent de PokéAPI).
    swarm = _encounters(
        preview_db, "v.identifier = 'gold' AND l.identifier = 'johto-route-32' AND m.identifier = 'good-rod'"
    )
    assert ("magikarp", 35.0, "swarm-yes") in {(row[2], row[6], row[8]) for row in swarm}


def test_bug_catching_contest(preview_db: sqlite3.Connection) -> None:
    scyther = _encounters(preview_db, "p.identifier = 'scyther' AND v.identifier = 'gold'")
    assert {(row[1], row[3], row[4], row[5], row[6], row[8]) for row in scyther} == {
        ("national-park", "walk", 13, 14, 5.0, "bug-catching-contest-yes")
    }


def test_one_off_encounters_and_notes(preview_db: sqlite3.Connection) -> None:
    notes = {
        (row[0], row[2]): row[7]
        for row in _encounters(preview_db, "v.version_group_id = ? AND e.note_fr IS NOT NULL", str(GOLD_SILVER_GROUP))
    }
    # Objet tenu forcé (BATTLETYPE_FORCEITEM) et Léviator chromatique (BATTLETYPE_FORCESHINY), lus dans les scripts.
    assert notes[("gold", "ho-oh")] == "Tient toujours l'objet Cendre Sacrée"
    assert notes[("silver", "snorlax")].endswith("Tient toujours l'objet Restes")
    assert notes[("gold", "gyarados")] == "Toujours chromatique"
    assert notes[("gold", "onix")] == "Échange contre Chétiflor"
    assert notes[("silver", "sandshrew")] == "700 jetons"
    # Lugia est dans sa salle (PokéAPI le range au 2e sous-sol), à 70 dans Or et 40 dans Argent.
    lugia = _encounters(preview_db, "v.version_group_id = 3 AND p.identifier = 'lugia'")
    assert {(row[0], row[1], row[4]) for row in lugia} == {
        ("gold", "whirl-islands/b3f", 70),
        ("silver", "whirl-islands/b3f", 40),
    }
    roaming = _encounters(preview_db, "p.identifier = 'suicune' AND v.identifier = 'gold'")
    assert {(row[1], row[3], row[6], row[8]) for row in roaming} == {
        ("roaming-johto/area", "roaming-grass", None, "story-progress-awakened-beasts")
    }


def test_roaming_pokemon_are_on_johto_routes(preview_db: sqlite3.Connection) -> None:
    maps = {
        row[0]
        for row in preview_db.execute(
            """SELECT m.identifier FROM map_area ma JOIN map m ON m.id = ma.map_id
               JOIN location_area la ON la.id = ma.location_area_id JOIN location l ON l.id = la.location_id
               WHERE l.identifier = 'roaming-johto'"""
        )
    }
    # RoamMaps : toutes les routes terrestres de Johto, sans les Routes 40 et 41.
    assert maps == {f"route-{n}" for n in (*range(29, 40), *range(42, 47))}


def test_version_specific_map_objects(preview_db: sqlite3.Connection) -> None:
    rows = preview_db.execute(
        """SELECT o.name_fr, o.level, v.identifier FROM map_object o JOIN version v ON v.id = o.version_id
           ORDER BY o.name_fr, v.identifier"""
    ).fetchall()
    assert rows == [("Ho-Oh", 40, "gold"), ("Ho-Oh", 70, "silver"), ("Lugia", 70, "gold"), ("Lugia", 40, "silver")]


def test_items_and_areas_absent_from_pokeapi(preview_db: sqlite3.Connection) -> None:
    item = preview_db.execute(
        "SELECT id, name_fr, category, description_fr FROM item WHERE identifier = 'berserk-gene'"
    ).fetchone()
    assert item == (100001, "ADN Berzerk", "held-items", "Booste l'attaque mais rend confus.")
    hidden = preview_db.execute(
        """SELECT m.identifier FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = 3 AND o.item_id = 100001 AND o.kind = 'hidden_item'"""
    ).fetchall()
    assert hidden == [("cerulean-city",)]
    areas = dict(preview_db.execute("SELECT identifier, name_fr FROM location_area WHERE id >= 100000"))
    assert areas == {
        "item-rooms": "Mont Argenté (salles des objets)",
        "": "Doublonville",
        "gym": "Arène d'Azuria",
        "port": "Port d'Oliville",
    }


def test_wild_tables_have_their_terrain(gold_silver_repo: Gen2PretRepo) -> None:
    """Chaque table du jeu porte sur un terrain de sa carte : herbes ou sol pour la marche, eau pour le surf."""
    needed = {"walk": ("grass", "floor"), "surf": ("water",), "headbutt": ("tree",), "rock-smash": ("rock",)}
    for table in wild_tables(gold_silver_repo, "_GOLD"):
        pret_map = gold_silver_repo.maps[table.map_const]
        if table.method in needed and table.map_const != "SAFARI_ZONE_BETA":
            cells = wild_cells(gold_silver_repo, pret_map)
            assert any(cells[kind] for kind in needed[table.method]), table
        if table.method.endswith("-rod"):
            assert has_water(gold_silver_repo, pret_map), table


def test_special_battles(gold_silver_repo: Gen2PretRepo) -> None:
    battles = {(battle.map_const, battle.species, battle.battle_type) for battle in special_battles(gold_silver_repo)}
    assert battles == {
        ("LAKE_OF_RAGE", "GYARADOS", "BATTLETYPE_FORCESHINY"),
        ("TIN_TOWER_ROOF", "HO_OH", "BATTLETYPE_FORCEITEM"),
        ("VERMILION_CITY", "SNORLAX", "BATTLETYPE_FORCEITEM"),
        ("WHIRL_ISLAND_LUGIA_CHAMBER", "LUGIA", "BATTLETYPE_FORCEITEM"),
    }


def test_a_map_with_random_encounters_has_one_area() -> None:
    assert _single_area("ROUTE_29", [185]) == 185
    with pytest.raises(ValueError, match="ROUTE_29 a des rencontres aléatoires et 2 zones"):
        _single_area("ROUTE_29", [185, 795])


def test_stale_transfer_only_rows_are_reported(preview_database: Path, tmp_path: Path) -> None:
    copy = tmp_path / "pokedex.db"
    shutil.copy(preview_database, copy)
    connection = sqlite3.connect(copy)
    try:
        # Bulbizarre devient obtenable dans Or, et ses évolutions avec lui : leurs lignes de transfer_only.csv n'ont
        # plus lieu d'être.
        connection.execute(
            """INSERT INTO encounter SELECT max(id) + 1, 4, 185, 1, 18, 5, 5, NULL, 1, NULL FROM encounter"""
        )
        connection.commit()
    finally:
        connection.close()
    assert "transfer_only.csv : Pokémon obtenables dans la génération 2 : [1, 2, 3]" in validate(copy)


def test_gold_silver_are_in_the_app(builder: DatabaseBuilder) -> None:
    assert GOLD_SILVER in builder.games
