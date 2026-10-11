"""Rencontres fixes des remakes : positions, accès et sources épinglées."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pokemaps_data.games import FIRERED_LEAFGREEN
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_fixed import fixed_encounters
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate_remake_fixed import validate_remake_fixed, validate_remake_rows

_ROOT = Path(__file__).resolve().parents[2]
_ASSETS = _ROOT / "app/src/main/assets"


def _catalog() -> dict[str, object]:
    return json.loads((_ASSETS / "maps/firered-leafgreen/fixed_encounters.json").read_text("utf-8"))


def test_remake_fixed_catalog() -> None:
    validate_remake_fixed(_ASSETS)
    for rows in _catalog()["versions"].values():
        positions = {row["pokemon"]: (row["x"], row["y"]) for row in rows}
        assert positions["SPECIES_HO_OH"] == (9, 6)
        assert positions["SPECIES_DEOXYS"] == (15, 3)
        snorlax = [row for row in rows if row["pokemon"] == "SPECIES_SNORLAX"]
        assert all(any(req["subject"] == "FLAG_GOT_POKE_FLUTE" for req in row["requirements"]) for row in snorlax)
        events = [row for row in rows if row["event"]]
        assert all(any(req["subject"].startswith("FLAG_ENABLE_SHIP_") for req in row["requirements"]) for row in events)


@pytest.mark.parametrize("field,value", [("level", 1), ("event", True), ("x", -1), ("requirements", [])])
def test_invalid_fixed_encounter_is_rejected(field: str, value: object) -> None:
    rows = deepcopy(_catalog()["versions"]["firered"])
    rows[0][field] = value
    with pytest.raises(ValueError, match="firered"):
        validate_remake_rows("firered", rows)


@pytest.mark.pipeline
def test_remake_fixed_catalog_matches_pinned_sources(source_cache_ready: None) -> None:
    repo = Gen3PretRepo(pret_dir(_ROOT / "tools/.cache", "pokefirered"), FIRERED_LEAFGREEN.pret_versions)
    for version, rows in _catalog()["versions"].items():
        assert fixed_encounters(repo, version) == rows
