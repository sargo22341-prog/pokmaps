"""Recette du lot HGSS après génération explicite ; aucun téléchargement pendant les tests."""

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.maps_render_hgss import HgssRenderer, camera_cotangent
from pokemaps_data.pret_hgss_maps import PROOF_MAPS, HgssMapRepo
from pokemaps_data.sources import HGSS_PRET_COMMIT
from pokemaps_data.validate_hgss_maps import validate_proof, validate_sources

_ROOT = Path(__file__).resolve().parents[2]
_NATIVE = _ROOT / "tools/.cache/hgss-qualification"
_PREVIEW = _ROOT / "tools/build/preview/hgss-maps"

pytestmark = pytest.mark.pipeline


def test_pinned_resources_are_available_without_rom() -> None:
    files = validate_sources(_NATIVE)
    assert "files/a/0/6/5" in files
    assert "files/a/0/4/0" in files
    assert "files/a/1/4/8" in files


@pytest.mark.parametrize("version", ["heartgold", "soulsilver"])
def test_native_geometry_warps_collision_actor_and_heights(version: str) -> None:
    repo = HgssMapRepo(_NATIVE, version)
    proof = validate_proof(repo)
    assert proof["return_links"] == [
        {"outside": 60, "warp": 0, "inside": 61, "anchor": 0},
        {"outside": 60, "warp": 4, "inside": 62, "anchor": 0},
    ]
    assert len(proof["route_29_boundary"]) == 7
    assert len(proof["overlapping_surfaces"]) == 118
    assert proof["overlapping_surfaces"][0] == {"x": 97, "z": 377, "attribute": 0x15, "heights": [688128, 851968]}
    assert repo.blocks(repo.headers[60]) == ((21, 12, 0, 0),)
    assert repo.blocks(repo.headers[61]) == ((0, 0, 244, 0),)
    renderer = HgssRenderer(repo)
    for name in PROOF_MAPS:
        header = next(h for h in repo.headers.values() if h.constant == f"MAP_{name}")
        for _, _, block, altitude in repo.blocks(header):
            assert renderer.triangles(header, block, altitude)
    assert camera_cotangent(_NATIVE, repo.headers[60]) > 0
    frame, source = renderer.actor_image("SPRITE_DOCTOR")
    assert frame.size == (32, 32) and frame.getbbox() is not None
    assert source.endswith(".NSBTX")


def test_generated_preview_inventory_and_two_versions_agree() -> None:
    path = _PREVIEW / "inventory.json"
    assert path.is_file(), "Préparer la preuve : python tools/build_data.py --hgss-maps-only"
    inventory = json.loads(path.read_text(encoding="utf-8"))
    assert set(inventory) == {p.relative_to(_PREVIEW).as_posix() for p in _PREVIEW.rglob("*") if p.is_file()} - {
        "inventory.json"
    }
    for relative, expected in inventory.items():
        assert hashlib.sha256((_PREVIEW / relative).read_bytes()).hexdigest() == expected, relative
    proof = json.loads((_PREVIEW / "proof.json").read_text(encoding="utf-8"))
    assert proof["commit"] == HGSS_PRET_COMMIT
    assert proof["sources"] == validate_sources(_NATIVE)
    first, second = proof["versions"]
    assert first["version"] == "heartgold" and second["version"] == "soulsilver"
    assert first["maps"] == second["maps"] and first["proof"] == second["proof"]
    for version in (first, second):
        for name, record in zip(PROOF_MAPS, version["maps"], strict=True):
            folder = _PREVIEW / version["version"] / name.lower()
            with Image.open(folder / "map.png") as image:
                assert hashlib.sha256(image.tobytes()).hexdigest() == record["pixels_sha256"]
            assert record["actor"]["sprite_source"] in proof["sources"]
            if record["lower"]:
                assert record["lower"]["pixels_sha256"] != record["pixels_sha256"]
