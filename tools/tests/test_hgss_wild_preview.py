"""Intégrité des aperçus HGSS et refus des prérequis périmés, sans cache ni réseau."""

import json
from pathlib import Path

import pytest

from pokemaps_data import preview_wild_hgss as preview
from pokemaps_data.sources import HGSS_PRET_COMMIT


def _preview(folder: Path) -> Path:
    maps = folder / "hgss-maps"
    maps.mkdir()
    (maps / "inventory.json").write_text("{}\n", encoding="utf-8")
    target = folder / "hgss-encounters"
    target.mkdir()
    sources = json.loads(preview._MANIFEST.read_text(encoding="utf-8"))
    table = {
        "version": "heartgold",
        "bank": 1,
        "method": "walk",
        "rate": 20,
        "configuration": {"period": "day", "radio": "off", "swarm": False, "national": False, "weekday": 0},
        "slots": [{"species": 16, "minimum": 2, "maximum": 4, "chance": 100}],
    }
    catalog = {
        "commit": HGSS_PRET_COMMIT,
        "versions": ["heartgold", "soulsilver"],
        "distributions": [table],
        "headbutt": [],
    }
    preview._write_preview(
        target, catalog, {"differences": [], "equal": 1}, sources, preview._digest(maps / "inventory.json")
    )
    return target


def test_committed_proof_keeps_current_sources_and_generation_recipe() -> None:
    proof_path = Path(__file__).resolve().parents[2] / "docs/generations/rencontres-hgss-preuve.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    manifest = json.loads(preview._MANIFEST.read_text(encoding="utf-8"))
    assert all(proof["sources"][key] == value for key, value in manifest.items())
    assert proof["sources"]["recipe"] == preview._recipe()
    assert len(proof["rock_differences"]) == 20
    assert len(proof["source_only"]) == 8


def test_preview_rejects_modified_output_and_stale_maps(tmp_path: Path) -> None:
    target = _preview(tmp_path)
    preview.check_encounters_preview(target)
    (tmp_path / "hgss-maps/inventory.json").write_text('{"changed": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="cartographique"):
        preview.check_encounters_preview(target)
    (target / "summary.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="modifié"):
        preview.check_encounters_preview(target)


def test_preview_rejects_stale_recipe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _preview(tmp_path)
    monkeypatch.setattr(preview, "_recipe", lambda: {"changed": "recipe"})
    with pytest.raises(ValueError, match="recette"):
        preview.check_encounters_preview(target)


def test_validation_failure_preserves_existing_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _preview(tmp_path)
    before = (target / "inventory.json").read_bytes()
    monkeypatch.setattr(preview, "fetch_pokeapi_csv", lambda _cache: tmp_path)

    def reject_source(_root: Path, _api: Path) -> dict:
        raise ValueError("HGSS : source modifiée")

    monkeypatch.setattr(preview, "validate_sources", reject_source)
    with pytest.raises(ValueError, match="source modifiée"):
        preview.build_hgss_encounters(tmp_path / "cache", tmp_path, tmp_path / "assets")
    assert (target / "inventory.json").read_bytes() == before
    preview.check_encounters_preview(target)
