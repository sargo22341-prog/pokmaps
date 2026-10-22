"""Recette des rencontres HGSS au commit épinglé : deux cartouches, sans réseau."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest

from pokemaps_data.catalog_wild_hgss import encounter_catalog
from pokemaps_data.compare_wild_hgss import compare_tables
from pokemaps_data.encounters_hgss import Configuration, Period, Radio, filter_distributions
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_hgss_wild import read_trees, read_wild
from pokemaps_data.preview_wild_hgss import validate_comparison, validate_sources
from pokemaps_data.sources import POKEAPI_COMMIT

_TOOLS = Path(__file__).resolve().parents[1]


@pytest.mark.pipeline
def test_all_hgss_encounters_match_pokeapi_except_proven_rock_weights() -> None:
    root = _TOOLS / ".cache/hgss-qualification"
    api_root = _TOOLS / ".cache" / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    validate_sources(root, api_root)
    api = PokeApi(api_root)
    tables, headers = read_wild(root)
    trees = read_trees(root)
    assert len(tables) == 14616 and len(trees) == 252
    assert {i for i, values in headers.items() if not values} == {45, 47, 49, 50, 64, 90, 138}
    assert all(sum(s.chance for s in table.slots) == 100 for table in (*tables, *trees))
    report = compare_tables(tables, api)
    validate_comparison(report)
    assert report["equal"] == 14256
    assert Counter(row["category"] for row in report["differences"]) == {"probabilites": 360}
    assert len({(r["version"], r["bank"]) for r in report["differences"]}) == 20
    assert len(report["source_only"]) == 8
    catalog = encounter_catalog(root, tables, trees, headers, api)
    assert catalog["radio_rate_effects"]["march"]["first_roll_delta"] == 25
    assert catalog["radio_rate_effects"]["lullaby"]["first_roll_delta"] == -25
    assert len(catalog["headbutt_context"]["trees"]) == 60
    assert set(catalog["headbutt_context"]["regular_tree_lookup"]) == {"1", "2", "3", "4", "5Plus"}
    assert "honey-tree" not in catalog["methods_fr"]
    assert report["area_bindings"][0] == 184 and report["area_bindings"][1] == 185
    proof = json.loads((_TOOLS.parent / "docs/generations/rencontres-hgss-preuve.json").read_text(encoding="utf-8"))
    for name, value in (("encounters.json", catalog), ("comparison.json", report)):
        encoded = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == proof["output_inventory"][name]


@pytest.mark.pipeline
def test_native_route29_versions_and_night_fishing_replacements() -> None:
    tables, _ = read_wild(_TOOLS / ".cache/hgss-qualification")
    morning = Configuration(Period.MORNING)
    hg = next(t for t in filter_distributions(tables, "heartgold", "walk", morning) if t.bank == 1)
    ss = next(t for t in filter_distributions(tables, "soulsilver", "walk", morning) if t.bank == 1)
    assert (hg.slots[7].species, hg.slots[7].minimum) == (161, 2)
    assert (ss.slots[7].species, ss.slots[7].minimum) == (19, 4)
    night = Configuration(Period.NIGHT)
    table = next(t for t in filter_distributions(tables, "heartgold", "good-rod", night) if t.bank == 0)
    assert table.slots[3].species == 90
    radio = Configuration(Period.NIGHT, Radio.HOENN, True, True, 2)
    table = next(t for t in filter_distributions(tables, "heartgold", "walk", radio) if t.bank == 1)
    assert [s.species for s in table.slots[2:6]] == [311, 311, 312, 312]
