"""Recette du catalogue HGSS intégral et des états visuels depuis les sources épinglées."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from pokemaps_data.catalog_maps_hgss import passage_catalog, read_catalog
from pokemaps_data.catalog_safari_hgss import safari_catalog
from pokemaps_data.dynamic_props_hgss import read_dynamic_props
from pokemaps_data.navigation_hgss import script_navigation
from pokemaps_data.pret_hgss_maps import HgssMapRepo
from pokemaps_data.sources_atlas_hgss import validate_atlas_sources
from pokemaps_data.validate_johto_hgss import check_johto_preview

_ROOT = Path(__file__).resolve().parents[2]
_NATIVE = _ROOT / "tools/.cache/hgss-qualification"
_PREVIEW = _ROOT / "tools/build/preview/hgss-maps"
pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize("version", ["heartgold", "soulsilver"])
def test_full_catalog_covers_kanto_facilities_and_native_scripted_travel(version: str) -> None:
    repo = HgssMapRepo(_NATIVE, version)
    entries = read_catalog(repo)
    selected = {e.header for e in entries if e.scope != "excluded"}
    assert len(selected) == 496
    assert len(passage_catalog(repo, entries, "atlas")) == 1314
    scripted = script_navigation(repo, selected)
    transports = {(p["source"], p["destination"]) for p in scripted if "transport" in p}
    assert transports == {(330, 307), (387, 307), (519, 401), (520, 198)}
    assert any(p["source"] == 448 and p["command"] == "MoveWarp" for p in scripted)
    assert all((repo.root / p.source).is_file() for p in read_dynamic_props())
    safari = safari_catalog(repo)
    assert len(safari["templates"]) == 12 and len(safari["initial_sets"]) == 10
    assert safari["initial_sets"][0] == [0, 7, 1, 5, 3, 6]
    assert len(safari["slots"]) == 6 and safari["runtime_header"] == 357


def test_generated_atlas_includes_layers_and_all_source_references() -> None:
    check_johto_preview(_PREVIEW)
    catalog = json.loads((_PREVIEW / "atlas/catalog.json").read_text(encoding="utf-8"))
    assert catalog["sources"] == validate_atlas_sources(_NATIVE)
    repo = HgssMapRepo(_NATIVE, "heartgold")
    entries = read_catalog(repo)
    assert catalog["inventory"] == [asdict(e) for e in entries]
    assert len(catalog["maps"]) == 496
    assert {p["id"] for p in catalog["plans"] if p["layout"] == "native"} == {
        "johto-exterieurs",
        "kanto-exterieurs",
    }
    lookup = {record["header"]: record for record in catalog["maps"]}
    assert lookup[145]["layers"] and lookup[151]["layers"] and lookup[454]["layers"]
    assert lookup[349]["layers"]
    assert lookup[456]["nonvisual_slices"]
    for record in catalog["maps"]:
        native = json.loads((_PREVIEW / "atlas" / record["image"]).with_name("native.json").read_text(encoding="utf-8"))
        expected = [asdict(p) for p in read_dynamic_props() if p.header == record["header"]]
        assert native["dynamic_props"] == json.loads(json.dumps(expected))
    assert catalog["script_navigation"] == script_navigation(repo, set(lookup))
    assert catalog["safari"] == safari_catalog(repo)
    for record in catalog["maps"]:
        for layer in record["layers"]:
            assert layer["origin_pixels"] == record["origin_pixels"]
            assert layer["size"] == record["size"]
