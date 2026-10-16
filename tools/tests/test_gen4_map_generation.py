"""Publication par famille et rafraîchissement des catalogues sans rendu coûteux."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemaps_data import maps_gen4, maps_refresh_gen4
from pokemaps_data.maps_layout import identifier
from pokemaps_data.maps_layout_gen4 import MatrixBlock, MatrixDisplay


def test_completed_family_survives_failure_of_the_other(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "sinnoh-maps"
    monkeypatch.setattr(maps_gen4, "fetch_pret", lambda *_: tmp_path)
    monkeypatch.setattr(maps_gen4, "Gen4PretRepo", lambda *_: None)
    monkeypatch.setattr(maps_gen4, "selected_headers", lambda _: {})
    monkeypatch.setattr(maps_gen4, "_prepare", lambda *_: ())

    def build(folder: Path, game: object, _workers: int, _source: tuple) -> dict:
        if game.version_group == "diamond-pearl":
            raise ValueError("Diamant : texture absente")
        folder.mkdir()
        (folder / "pixels").write_bytes(b"valide")
        return {"version_group": game.version_group}

    monkeypatch.setattr(maps_gen4, "_build_game", build)
    with pytest.raises(ValueError, match="texture absente"):
        maps_gen4.build_gen4_maps(tmp_path, output)
    assert (output / "platinum/pixels").read_bytes() == b"valide"
    assert json.loads((output / "generation-report.json").read_text()) == [{"version_group": "platinum"}]
    assert not (output / "diamond-pearl").exists()


def test_catalog_refresh_refuses_removed_or_added_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    layout = MatrixDisplay("MONDE", 0, (10,), (MatrixBlock(0, 0, 1, 10, 0),), (0, 0, 512, 512))
    monkeypatch.setattr(maps_refresh_gen4, "displays", lambda *_: (layout,))
    monkeypatch.setattr(maps_refresh_gen4, "selected_headers", lambda _: {})
    repo = SimpleNamespace(variant="platinum", matrices={0: SimpleNamespace(blocks=((1,),))})
    source = {"const": "MONDE", "matrix": 0, "headers": [10], "base": None, "blocks": [], "bounds": layout.bounds}
    with pytest.raises(ValueError, match="sélection des blocs modifiée"):
        maps_refresh_gen4._catalog_atlases(repo, {"displays": [source]})
    source["blocks"] = [{"offset": [0, 0], "request": {"block": 1}}]
    assert maps_refresh_gen4._catalog_atlases(repo, {"displays": [source]})[0].display == layout


def test_editorial_level_removal_preserves_the_native_tiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(maps_refresh_gen4, "_skipped_levels", lambda _: {"MAISON"})
    native = tmp_path / identifier("MAISON")
    lower = tmp_path / identifier("MAISON_LOWER")
    native.mkdir()
    lower.mkdir()
    (native / "pixels").write_bytes(b"sol")
    (lower / "pixels").write_bytes(b"faux sous-sol")
    metadata = {
        "headers": [{"index": 1, "constant": "MAISON"}],
        "displays": [
            {"const": "MAISON", "headers": [1], "base": None},
            {"const": "MAISON_LOWER", "headers": [1], "base": "MAISON"},
        ],
    }
    (tmp_path / "levels.json").write_text('[{"display": "MAISON"}]', encoding="utf-8")
    maps_refresh_gen4._prune_levels(None, metadata, tmp_path)
    assert (native / "pixels").read_bytes() == b"sol" and not lower.exists()
    assert len(metadata["displays"]) == 1
    assert json.loads((tmp_path / "levels.json").read_text()) == []
