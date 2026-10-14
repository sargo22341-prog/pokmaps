"""Régressions des équipes et dons oubliés dans les trois jeux de Johto."""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pokemaps_data.validate import validate


@pytest.mark.parametrize("group", [3, 4])
def test_all_seven_rival_battles_have_three_starter_teams(db: sqlite3.Connection, group: int) -> None:
    rivals = db.execute(
        """SELECT o.id, count(DISTINCT t.team), count(DISTINCT t.variant_pokemon_id)
           FROM map_object o JOIN map m ON m.id = o.map_id
           LEFT JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE m.version_group_id = ? AND o.trainer_class IN ('rival1', 'rival2')
           GROUP BY o.id""",
        (group,),
    ).fetchall()
    assert len(rivals) == 7
    assert all(teams == starters == 3 for _, teams, starters in rivals)
    first = db.execute(
        """SELECT t.variant_pokemon_id, t.pokemon_id, t.level
           FROM trainer_pokemon t JOIN map_object o ON o.id = t.map_object_id
           JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND m.identifier = 'cherrygrove-city'""",
        (group,),
    ).fetchall()
    assert set(first) == {(152, 155, 5), (155, 158, 5), (158, 152, 5)}


@pytest.mark.parametrize("group", [3, 4])
def test_cal_uses_default_level_fifty_team(db: sqlite3.Connection, group: int) -> None:
    rows = db.execute(
        """SELECT t.pokemon_id, t.level FROM trainer_pokemon t
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND o.trainer_class = 'cal' ORDER BY t.slot""",
        (group,),
    ).fetchall()
    assert rows == [(154, 50), (157, 50), (160, 50)]


@pytest.mark.parametrize(("group", "trainers", "teams"), [(3, 28, 56), (4, 24, 76)])
def test_phone_rematches_stay_on_the_original_character(
    db: sqlite3.Connection, group: int, trainers: int, teams: int
) -> None:
    rows = db.execute(
        """SELECT t.map_object_id, t.team, t.rematch FROM trainer_pokemon t
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND t.rematch IS NOT NULL GROUP BY t.map_object_id, t.team""",
        (group,),
    ).fetchall()
    assert len(rows) == teams
    assert len({obj for obj, _, _ in rows}) == trainers
    assert all(team == rematch + 1 for _, team, rematch in rows)


@pytest.mark.parametrize("group", [3, 4])
def test_scene_gifts_are_attached_to_their_givers(db: sqlite3.Connection, group: int) -> None:
    gifts = set(
        db.execute(
            """SELECT m.identifier, o.name_fr, i.identifier, n.quantity, v.identifier
           FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           JOIN item i ON i.id = n.item_id LEFT JOIN version v ON v.id = n.version_id
           WHERE m.version_group_id = ? AND n.kind = 'gift_item'""",
            (group,),
        )
    )
    assert ("radio-tower-5f", "Faux Directeur", "basement-key", 1, None) in gifts
    for item, version in (
        (("rainbow-wing", "gold"), ("silver-wing", "silver")) if group == 3 else (("clear-bell", None),)
    ):
        assert ("radio-tower-5f", "Directeur de la Tour Radio", item, 1, version) in gifts
        assert ("radio-tower-5f", "Faux Directeur", item, 1, version) not in gifts
    assert any(place == "elms-lab" and item == "potion" and quantity == 1 for place, _, item, quantity, _ in gifts)
    assert any(place == "elms-lab" and item == "poke-ball" and quantity == 5 for place, _, item, quantity, _ in gifts)
    assert any(place == "mr-pokemons-house" and item == "mystery-egg" for place, _, item, _, _ in gifts)
    assert any(place == "dragons-den-b1f" and item == "tm24" for place, _, item, _, _ in gifts)


@pytest.mark.parametrize("group", [3, 4])
def test_security_camera_grunts_have_both_teams(db: sqlite3.Connection, group: int) -> None:
    teams = db.execute(
        """SELECT o.id, group_concat(t.pokemon_id) FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE m.version_group_id = ? AND m.identifier = 'team-rocket-base-b1f'
             AND o.trainer_class = 'gruntm' GROUP BY o.id""",
        (group,),
    ).fetchall()
    assert {party for _, party in teams} >= {"96,41", "41,88,19"}


def test_trainer_held_items_survive_export(db: sqlite3.Connection) -> None:
    held = {
        row[0]
        for row in db.execute(
            """SELECT DISTINCT i.identifier FROM trainer_pokemon t JOIN item i ON i.id = t.held_item_id
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id IN (3, 4)"""
        )
    }
    assert {"oran-berry", "focus-band", "kings-rock"} <= held
    assert (
        db.execute(
            """SELECT count(*) FROM trainer_pokemon t JOIN map_object o ON o.id = t.map_object_id
           JOIN map m ON m.id = o.map_id WHERE m.version_group_id IN (5, 6, 7) AND t.held_item_id IS NOT NULL"""
        ).fetchone()[0]
        > 0
    )


@pytest.mark.parametrize(("column", "value"), [("held_item_id", 999999), ("rematch", 0)])
def test_validation_rejects_unknown_held_item_or_invalid_rematch(
    db: sqlite3.Connection, database: Path, column: str, value: int
) -> None:
    db.execute(
        f"UPDATE trainer_pokemon SET {column} = ? WHERE rowid = (SELECT min(rowid) FROM trainer_pokemon)", (value,)
    )
    db.commit()
    path = Path(db.execute("PRAGMA database_list").fetchone()[2])
    assert path != database
    assert any("équipe de dresseur incohérente" in error for error in validate(path))


def test_johto_guides_keep_the_actual_calendar_and_legend_requirements() -> None:
    path = Path(__file__).resolve().parents[2] / "app/src/main/res/values/strings_guides.xml"
    texts = {node.attrib["name"]: " ".join("".join(node.itertext()).split()) for node in ET.parse(path).getroot()}
    assert "lundi matin" in texts["guide_day_monday_text"]
    assert "dimanche matin" not in texts["guide_day_sunday_text"]
    assert "Ruban Rose" in texts["guide_day_tuesday_text"]
    assert "Cascade sert à la remonter" in texts["guide_johto_legends_text"]
    assert "Dans Cristal, battez la Ligue" in texts["guide_hooh_text"]
