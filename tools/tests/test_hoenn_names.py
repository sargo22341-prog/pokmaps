"""Noms personnels des Champions et du Conseil 4, distincts des classes génériques."""

import sqlite3

import pytest


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_hoenn_leaders_and_elite_four_are_named(db: sqlite3.Connection, version: str) -> None:
    names = {
        row[0]
        for row in db.execute(
            """SELECT o.name_fr FROM map_object o JOIN version v ON v.id = o.version_id
               WHERE v.identifier = ? AND o.kind = 'trainer'""",
            (version,),
        )
    }
    expected = {"Roxanne", "Bastien", "Voltère", "Adriane", "Norman", "Alizée", "Lévy et Tatia"}
    expected |= {"Damien", "Spectra", "Glacia", "Aragon"}
    expected.add("Juan" if version == "emerald" else "Marc")
    assert expected <= names
    assert not names & {"Champion", "Conseil 4"}
