"""Profils et événements structurés de la base distribuée, sans dépendre des notes françaises."""

import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pokemaps_data.achievement_resources import build_achievement_resources
from pokemaps_data.validate import CHECKS
from pokemaps_data.validate_profiles import validate_profiles


@pytest.mark.parametrize(
    "version,form,attack",
    [(7, "normal", 150), (8, "normal", 150), (9, "speed", 95), (10, "attack", 180), (11, "defense", 70)],
)
def test_deoxys_profile_and_sprite_follow_the_cartridge(
    db: sqlite3.Connection, version: int, form: str, attack: int
) -> None:
    assert db.execute(
        "SELECT identifier, attack FROM pokemon_form WHERE version_id = ? AND pokemon_id = 386 AND is_default = 1",
        (version,),
    ).fetchall() == [(f"deoxys-{form}", attack)]


def test_castform_has_four_forms_and_one_default_in_each_gba_game(db: sqlite3.Connection) -> None:
    assert db.execute(
        """SELECT version_id, count(*), sum(is_default) FROM pokemon_form
           WHERE pokemon_id = 351 AND version_id BETWEEN 7 AND 11 GROUP BY version_id"""
    ).fetchall() == [(version, 4, 1) for version in range(7, 12)]


def test_forms_reject_an_invalid_default(db: sqlite3.Connection) -> None:
    db.execute("UPDATE pokemon_form SET is_default = 0 WHERE version_id = 9 AND pokemon_id = 386")
    assert any("forme par défaut" in error for error in validate_profiles(db))


@pytest.mark.parametrize(
    "statement,label",
    [
        ("UPDATE encounter SET external_event = 2 WHERE id = (SELECT min(id) FROM encounter)", "rencontre"),
        ("UPDATE npc_offer SET external_event = -1 WHERE id = (SELECT min(id) FROM npc_offer)", "offre"),
        ("UPDATE map SET external_event_key = NULL WHERE event_entrance > 0", "entrée événementielle"),
    ],
)
def test_invalid_external_metadata_is_rejected(db: sqlite3.Connection, statement: str, label: str) -> None:
    db.execute(statement)
    assert any(label in error for error in validate_profiles(db))


def test_an_item_description_cannot_disappear(db: sqlite3.Connection) -> None:
    db.execute("UPDATE item SET description_fr = NULL WHERE identifier = 'orange-mail'")
    query = next(query for label, query in CHECKS if label == "objet sans description française hors CT/CS")
    assert db.execute(query).fetchall()


def test_external_event_metadata_survives_editorial_changes(db: sqlite3.Connection) -> None:
    count = db.execute("SELECT count(*) FROM encounter WHERE external_event = 1").fetchone()[0]
    assert count > 0
    db.execute("UPDATE encounter SET note_fr = NULL")
    assert db.execute("SELECT count(*) FROM encounter WHERE external_event = 1").fetchone()[0] == count
    # Les récompenses personnalisées du Bulletin restent au catalogue, hors des offres distribuées.
    assert db.execute("SELECT count(*) FROM npc_offer WHERE external_event NOT IN (0, 1)").fetchone()[0] == 0
    assert (
        db.execute(
            """SELECT count(*) FROM map m JOIN version_group vg ON vg.id = m.version_group_id
           WHERE m.event_entrance > 0 AND vg.generation_id <= 3"""
        ).fetchone()[0]
        == 7
    )
    assert db.execute(
        """SELECT version_group_id, count(*) FROM map WHERE event_entrance > 0 AND version_group_id IN (8, 9)
           GROUP BY version_group_id ORDER BY version_group_id"""
    ).fetchall() == [(8, 3), (9, 3)]


def test_achievement_resources_are_reproducible(tmp_path: Path) -> None:
    build_achievement_resources(tmp_path)
    resources = Path(__file__).resolve().parents[2] / "app/src/main/res/values"
    files = list(tmp_path.glob("*.xml"))
    assert len(files) == 11
    for path in files:
        assert path.read_bytes() == (resources / path.name).read_bytes()


def test_achievement_resources_share_repeated_texts(tmp_path: Path) -> None:
    build_achievement_resources(tmp_path)
    resources = Path(__file__).resolve().parents[2] / "app/src/main/res/values"
    existing = [path for path in resources.glob("*.xml") if not path.name.startswith("strings_achievements")]
    seen = set()
    for path in [*existing, *sorted(tmp_path.glob("*.xml"))]:
        for node in ET.parse(path).getroot().findall("string"):
            text = " ".join("".join(node.itertext()).replace("\\'", "'").replace('\\"', '"').split())
            if text.startswith("@string/"):
                continue
            if path.parent == tmp_path:
                assert text not in seen, f"Texte recopié au lieu d'une référence : {node.attrib['name']}"
            seen.add(text)
