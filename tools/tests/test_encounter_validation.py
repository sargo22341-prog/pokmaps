"""Les rencontres invalides échouent à la validation de la base, même si la somme SQL serait NULL."""

import sqlite3

import pytest

from pokemaps_data.validate import CHECKS


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
