"""Catalogues fixes Hoenn : variantes, niveaux et provenance pret."""

import json
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_fixed import fixed_encounters
from pokemaps_data.sources import PRET_COMMITS, pret_dir

_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("group", ["ruby-sapphire", "emerald"])
def test_fixed_catalog_versions_and_levels(group: str) -> None:
    catalog = json.loads((_ROOT / "app/src/main/assets/maps" / group / "fixed_encounters.json").read_text("utf-8"))
    assert catalog["commit"] == PRET_COMMITS[catalog["repo"]]
    for version, rows in catalog["versions"].items():
        assert len(rows) == (22 if version == "emerald" else 20)
        encounters = {(row["pokemon"], row["level"]) for row in rows}
        assert {(f"SPECIES_{name}", 40) for name in ("REGIROCK", "REGICE", "REGISTEEL")} <= encounters
        assert {("SPECIES_RAYQUAZA", 70), ("SPECIES_ELECTRODE", 30), ("SPECIES_KECLEON", 30)} <= encounters
        legends = {name for name, level in encounters if name in {"SPECIES_GROUDON", "SPECIES_KYOGRE"}}
        assert legends == (
            {"SPECIES_GROUDON", "SPECIES_KYOGRE"}
            if version == "emerald"
            else {"SPECIES_GROUDON" if version == "ruby" else "SPECIES_KYOGRE"}
        )
        assert {(name, 70 if version == "emerald" else 45) for name in legends} <= encounters
        island = [row for row in rows if row["event"]]
        assert {row["pokemon"] for row in island} == (
            {"SPECIES_LATIOS", "SPECIES_LATIAS"}
            if version == "emerald"
            else {"SPECIES_LATIAS" if version == "ruby" else "SPECIES_LATIOS"}
        )
        assert all(row["level"] == 50 and row["held_item"] == "ITEM_SOUL_DEW" for row in island)
        assert all(row["requirements"] and row["source"] and row["removal_flag"].startswith("FLAG_") for row in rows)


@pytest.mark.pipeline
def test_fixed_catalog_matches_pinned_events(source_cache_ready: None) -> None:
    for game in GEN3_GAMES:
        if game.pret_repo == "pokefirered":
            continue
        catalog = json.loads(
            (_ROOT / "app/src/main/assets/maps" / game.version_group / "fixed_encounters.json").read_text("utf-8")
        )
        repo = Gen3PretRepo(pret_dir(_ROOT / "tools/.cache", game.pret_repo), game.pret_versions)
        for version, _ in game.pret_versions:
            assert fixed_encounters(repo, version) == catalog["versions"][version]
