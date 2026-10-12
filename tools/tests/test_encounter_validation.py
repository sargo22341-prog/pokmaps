"""Les rencontres invalides échouent à la validation de la base, même si la somme SQL serait NULL."""

import sqlite3

import pytest

from pokemaps_data.validate import CHECKS


def test_unknown_encounter_identifier_cannot_reach_android(db: sqlite3.Connection) -> None:
    method = db.execute("SELECT id FROM encounter_method LIMIT 1").fetchone()[0]
    db.execute("UPDATE encounter_method SET identifier = 'unknown-method' WHERE id = ?", (method,))
    query = next(query for description, query in CHECKS if description == "méthode de rencontre non prise en charge")
    assert (method, "unknown-method") in db.execute(query).fetchall()


def test_unknown_learn_method_cannot_silently_disappear(db: sqlite3.Connection) -> None:
    db.execute("UPDATE pokemon_move SET method = 'unknown-method' WHERE rowid = (SELECT min(rowid) FROM pokemon_move)")
    query = next(query for description, query in CHECKS if description == "méthode d'apprentissage non prise en charge")
    assert db.execute(query).fetchall()


@pytest.mark.parametrize(
    "changes",
    ["chance = NULL", "chance = 0", "chance = 101", "min_level = 0", "max_level = 101", "quantity = 0"],
)
def test_invalid_random_encounter_is_detected(db: sqlite3.Connection, changes: str) -> None:
    encounter = db.execute(
        """SELECT e.id FROM encounter e JOIN encounter_method m ON m.id = e.method_id
           WHERE m.is_one_off = 0 LIMIT 1"""
    ).fetchone()[0]
    db.execute(f"UPDATE encounter SET {changes} WHERE id = ?", (encounter,))
    query = next(
        query
        for description, query in CHECKS
        if description == "rencontre avec niveaux, quantité ou probabilité invalides"
    )
    assert (encounter,) in db.execute(query).fetchall()
