"""Recette du catalogue Johto généré explicitement, avec les seules sources épinglées."""

import hashlib
from dataclasses import asdict
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.catalog_maps_hgss import (
    matrix_neighbors,
    passage_catalog,
    passage_surface,
    read_catalog,
    validate_catalog_geometry,
)
from pokemaps_data.maps_render_hgss import HgssRenderer
from pokemaps_data.pret_hgss_maps import HgssMapRepo
from pokemaps_data.preview_johto_hgss import validate_johto_sources
from pokemaps_data.validate_johto_hgss import check_johto_preview

_ROOT = Path(__file__).resolve().parents[2]
_NATIVE = _ROOT / "tools/.cache/hgss-qualification"
_PREVIEW = _ROOT / "tools/build/preview/hgss-maps"

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize("version", ["heartgold", "soulsilver"])
def test_johto_catalog_has_complete_native_references(version: str) -> None:
    repo = HgssMapRepo(_NATIVE, version)
    entries = read_catalog(repo)
    selected = {entry.header: entry for entry in entries if entry.scope == "johto"}
    assert len(entries) == 540 and len(selected) == 246
    assert 536 in selected and dict(repo.headers[536].fields)["regionNo"] == "MAP_REGION_KANTO"
    assert 183 not in selected and 82 not in selected
    validate_catalog_geometry(repo, entries)
    passages = passage_catalog(repo, entries)
    assert {p["source"] for p in passages if p["kind"] == "variable"} == {441, 446, 447}
    assert passage_surface(repo, 99, 3)["source"] == "editorial"
    assert passage_surface(repo, 151, 1)["candidates_fx32"] == (655360, 851968)
    neighbors = matrix_neighbors(repo, entries)
    assert {n["destination"] for n in neighbors if n["target_scope"] == "kanto"} == {31, 32}
    renderer = HgssRenderer(repo)
    for index in (75, 80, 139, 199, 206, 441, 446, 447, 486):
        header = repo.headers[index]
        for _, _, block, altitude in repo.blocks(header):
            assert renderer.triangles(header, block, altitude)


def test_johto_generated_images_plans_and_sources_are_consistent() -> None:
    catalog = check_johto_preview(_PREVIEW)
    assert catalog["sources"] == validate_johto_sources(_NATIVE)
    repo = HgssMapRepo(_NATIVE, "heartgold")
    assert catalog["inventory"] == [asdict(entry) for entry in read_catalog(repo)]
    assert len(catalog["maps"]) == 246
    assert sum(plan["layout"] == "native" for plan in catalog["plans"]) == 1
    for record in catalog["maps"]:
        with Image.open(_PREVIEW / "johto" / record["image"]) as image:
            assert image.size == tuple(record["size"])
            assert hashlib.sha256(image.tobytes()).hexdigest() == record["pixels_sha256"]
            assert image.getbbox() is not None
    assert catalog["matrix_neighbors"]
    for passage in catalog["passages"]:
        assert "source_surface" in passage
