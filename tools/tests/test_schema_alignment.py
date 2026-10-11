"""Le générateur et Room doivent annoncer la même version de schéma."""

import re
from pathlib import Path

from pokemaps_data.builder import SCHEMA_VERSION


def test_room_and_generator_schema_versions_match() -> None:
    root = Path(__file__).resolve().parents[2]
    source = root / "app/src/main/java/org/opensources/pokmaps/data/db/PokedexDatabase.kt"
    versions = re.findall(r"const val VERSION = (\d+)", source.read_text(encoding="utf-8"))
    assert versions == [str(SCHEMA_VERSION)]
