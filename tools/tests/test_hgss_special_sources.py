"""Provenance et exclusions HGSS vérifiées dans les sources épinglées."""

from pathlib import Path

import pytest

from pokemaps_data.obtainings_hgss import obtaining_catalog
from pokemaps_data.special_wild_hgss import read_special_wild
from pokemaps_data.validate_special_hgss import validate_obtainings, validate_special_wild

_ROOT = Path(__file__).resolve().parents[1] / ".cache/hgss-qualification"


@pytest.mark.pipeline
def test_all_special_tables_and_obtaining_provenances_are_validated() -> None:
    special = read_special_wild(_ROOT)
    validate_special_wild(special)
    assert len(special["safari"]) == 12
    contest = special["contest"]
    assert {r["slots"][0]["species"] for r in contest} == {10, 265}
    assert {r["slots"][0]["minimum"] for r in contest} == {7, 24}
    catalog = obtaining_catalog(_ROOT)
    validate_obtainings(catalog)
    assert len(catalog["scripts"]) == 62
    assert len(catalog["trades"]) == 13
    assert {r["given"] for r in catalog["trades"] if r["loan"]} == {21, 213}
    assert len(catalog["pokewalker"]["courses"]) == 27
    assert catalog["pokewalker"]["map_headers"] == []
    for row in catalog["scripts"]:
        if row["command"] == "GiveSpikyEarPichu" or row["native_location"] in ("D51R0201", "T03", "D52R0103"):
            assert row["ordinary_objective"] is False and row["exclusion_fr"]
    eggs = {n for r in catalog["scripts"] if r["kind"] == "egg" for n in r["species"]}
    assert eggs == {175, 179, 194, 218}
    roamers = {n for r in catalog["scripts"] if r["kind"] == "roamer" for n in r["species"]}
    assert roamers == {243, 244, 380, 381}
