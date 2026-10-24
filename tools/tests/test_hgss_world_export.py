"""Le réexport graphique refuse les changements de coordonnées et restaure un remplacement échoué."""

import json
from pathlib import Path

import pytest

from pokemaps_data import world_export_hgss


def test_world_export_rejects_any_non_graphical_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preview = tmp_path / "preview/hgss-maps/atlas"
    preview.mkdir(parents=True)
    (preview / "catalog.json").write_text(json.dumps(dict(maps=[dict(offset=[1, 2])])), encoding="utf-8")
    output = tmp_path / "assets/maps/heartgold-soulsilver"
    output.mkdir(parents=True)
    destination = output / "catalog.json"
    original = json.dumps(dict(source_catalog=dict(maps=[dict(offset=[1, 3])])))
    destination.write_text(original, encoding="utf-8")
    monkeypatch.setattr(world_export_hgss, "PREVIEW_DIR", tmp_path / "preview")
    monkeypatch.setattr(world_export_hgss, "check_johto_preview", lambda path: None)
    monkeypatch.setattr(world_export_hgss, "native_map_types", lambda path: {})
    monkeypatch.setattr(world_export_hgss, "application_catalog", lambda catalog, types: catalog)
    with pytest.raises(ValueError, match="maps modifié"):
        world_export_hgss.export_worlds(tmp_path / "cache", tmp_path / "assets")
    assert destination.read_text(encoding="utf-8") == original


def test_failed_world_replacement_restores_both_previous_regions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output, staging = tmp_path / "output", tmp_path / "staging"
    for parent, text in ((output, "précédent"), (staging, "nouveau")):
        for name in ("johto", "kanto"):
            (parent / name).mkdir(parents=True)
            (parent / name / "tile").write_text(text, encoding="utf-8")
    rename = Path.rename

    def fail_second_region(path: Path, target: Path) -> Path:
        if path == staging / "kanto":
            raise OSError("échec simulé")
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_second_region)
    with pytest.raises(OSError, match="échec simulé"):
        world_export_hgss._replace_worlds(output, staging, ("johto", "kanto"))
    for name in ("johto", "kanto"):
        assert (output / name / "tile").read_text(encoding="utf-8") == "précédent"
