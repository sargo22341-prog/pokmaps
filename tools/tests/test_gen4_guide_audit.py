"""Niveaux et lieux annoncés par les guides confrontés à la base livrée, sans cache."""

import re
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_RESOURCES = Path(__file__).resolve().parents[2] / "app/src/main/res/values"


def test_starting_guides_use_the_french_poketch_name() -> None:
    resources = {
        entry.attrib["name"]: "".join(entry.itertext())
        for entry in ET.parse(_RESOURCES / "strings_guides_sinnoh.xml").getroot()
    }
    # Nom français officiel, également employé par maps.csv et les traductions des succès.
    for version in ("dp", "pt"):
        text = resources[f"guide_sinnoh_start_{version}_text"]
        assert "Pokémontre" in text and "Pokétch" not in text


@pytest.mark.parametrize(
    "version,article,species,level",
    [
        (12, "rotom_dp", 479, 15),
        (13, "rotom_dp", 479, 15),
        (14, "rotom_pt", 479, 20),
        (12, "friday_dp", 425, 22),
        (13, "friday_dp", 425, 22),
        (14, "friday_pt", 425, 15),
        (12, "postgame_dp", 485, 70),
        (13, "postgame_dp", 485, 70),
        (14, "postgame_pt", 485, 50),
        (12, "postgame_dp", 487, 70),
        (13, "postgame_dp", 487, 70),
        (14, "summit_pt", 487, 47),
    ],
)
def test_guide_fixed_encounter_levels_match_the_cartridge(
    db: sqlite3.Connection, version: int, article: str, species: int, level: int
) -> None:
    resources = {
        entry.attrib["name"]: " ".join("".join(entry.itertext()).split())
        for path in _RESOURCES.glob("strings_guides_sinnoh*.xml")
        for entry in ET.parse(path).getroot()
    }
    text = resources[f"guide_sinnoh_{article}_text"]
    assert f"[[pokemon:{species}|" in text
    assert re.search(rf"niveau {level}\b", text)
    rows = db.execute(
        """SELECT DISTINCT o.level FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version v ON v.version_group_id = m.version_group_id
           WHERE v.id = ? AND o.kind = 'pokemon' AND o.pokemon_id = ?
             AND (o.version_id IS NULL OR o.version_id = v.id)""",
        (version, species),
    ).fetchall()
    assert (level,) in rows
