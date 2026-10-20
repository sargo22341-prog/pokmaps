"""Liens explicites des textes Sinnoh vérifiés par famille, sans build Android ni cache de sources."""

import re
import sqlite3
import xml.etree.ElementTree as ET
from contextlib import closing
from pathlib import Path

import pytest

_RESOURCES = Path(__file__).resolve().parents[2] / "app/src/main/res/values"


@pytest.mark.parametrize(("group", "other_variant"), [(8, "_pt_"), (9, "_dp_")], ids=["dp", "pt"])
def test_explicit_guide_links_exist_in_their_own_game(database: Path, group: int, other_variant: str) -> None:
    with closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as connection:
        places = {row[0] for row in connection.execute("SELECT identifier FROM map WHERE version_group_id=?", (group,))}
        pokemon = {row[0] for row in connection.execute("SELECT id FROM pokemon WHERE generation_id<=4")}
    files = sorted(_RESOURCES.glob("strings_guides_sinnoh*.xml"))
    assert len(files) == 3
    for path in files:
        for resource in ET.parse(path).getroot():
            name = resource.attrib["name"]
            if other_variant in name:
                continue
            text = resource.text or ""
            for place in re.findall(r"\[\[place:([^|]+)\|", text):
                assert place in places, (group, name, place)
            for species in re.findall(r"\[\[pokemon:(\d+)\|", text):
                assert int(species) in pokemon, (group, name, species)
