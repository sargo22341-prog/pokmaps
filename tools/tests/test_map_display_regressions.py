"""Contrats des repères corrigés, vérifiés sur les assets réellement embarqués."""

import sqlite3

import pytest

from pokemaps_data.application_hgss import validate_database


@pytest.mark.parametrize("version", [15, 16])
@pytest.mark.parametrize(
    "species,place,point",
    [(249, "whirl-islands-b3f-lugia-cave", (392, 529)), (250, "bell-tower-roof", (561, 2869))],
)
def test_hgss_scene_legends_have_one_fixed_marker(
    db: sqlite3.Connection, version: int, species: int, place: str, point: tuple[int, int]
) -> None:
    rows = db.execute(
        """SELECT m.identifier, o.x, o.y, o.level FROM map_object o JOIN map m ON m.id=o.map_id
           WHERE m.version_group_id=10 AND o.kind='pokemon' AND o.pokemon_id=? AND o.version_id=?""",
        (species, version),
    ).fetchall()
    assert rows == [(place, *point, 45 if (species, version) in {(249, 16), (250, 15)} else 70)]


def test_hgss_missing_legend_marker_is_an_error(db: sqlite3.Connection) -> None:
    db.execute(
        "DELETE FROM map_object WHERE pokemon_id=249 AND map_id IN (SELECT id FROM map WHERE version_group_id=10)"
    )
    assert validate_database(db) == [
        "HGSS : repère fixe absent ou incorrect : 249/15 (whirl-islands-b3f-lugia-cave)",
        "HGSS : repère fixe absent ou incorrect : 249/16 (whirl-islands-b3f-lugia-cave)",
    ]


@pytest.mark.parametrize("group,version", [(8, 12), (8, 13), (9, 14)])
@pytest.mark.parametrize("species", ["spiritomb", "arceus", "shaymin"])
def test_named_fixed_pokemon_has_one_marker(db: sqlite3.Connection, group: int, version: int, species: str) -> None:
    rows = db.execute(
        """SELECT o.kind, o.sprite FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN pokemon p ON p.id = o.pokemon_id WHERE m.version_group_id = ? AND p.identifier = ?
           AND (o.version_id IS NULL OR o.version_id = ?)""",
        (group, species, version),
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "pokemon"
    if species == "arceus":
        assert rows[0][1] == "156"


@pytest.mark.parametrize("group", [8, 9])
def test_celestic_surf_is_one_gift(db: sqlite3.Connection, group: int) -> None:
    rows = db.execute(
        """SELECT n.quantity FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id
           JOIN map m ON m.id = o.map_id JOIN item i ON i.id = n.item_id
           WHERE m.version_group_id = ? AND m.name_fr = 'Célestia' AND i.identifier = 'hm03'""",
        (group,),
    ).fetchall()
    assert rows == [(1,)]


@pytest.mark.parametrize("version", ["firered", "leafgreen"])
def test_route22_keeps_two_battles_per_starter_on_one_rival(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT count(DISTINCT o.id), count(DISTINCT t.team), count(DISTINCT t.variant_pokemon_id)
           FROM map_object o JOIN map m ON m.id = o.map_id JOIN version v ON v.id = o.version_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE m.identifier = 'route22' AND o.name_fr = 'Rival' AND v.identifier = ?""",
        (version,),
    ).fetchall()
    assert rows == [(1, 6, 3)]


@pytest.mark.parametrize("group", [8, 9])
def test_day_and_night_npc_poses_do_not_create_overlapping_characters(db: sqlite3.Connection, group: int) -> None:
    duplicates = db.execute(
        """SELECT m.identifier, o.sprite, o.x, o.y FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND o.kind IN ('trainer', 'npc') AND o.sprite IN ('34', '45')
           GROUP BY o.map_id, o.sprite, o.x, o.y HAVING count(*) > 1""",
        (group,),
    ).fetchall()
    assert duplicates == []
    joggers = db.execute(
        """SELECT o.kind FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND m.identifier IN ('route-209', 'header-route-209') AND o.sprite = '45'""",
        (group,),
    ).fetchall()
    assert joggers == [("trainer",), ("trainer",)]
