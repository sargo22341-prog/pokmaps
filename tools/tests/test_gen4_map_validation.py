"""Échecs visibles des catalogues, inventaires et planches de cartes DS."""

import json
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.maps_review_gen4 import _label_lines, region_thumbnail
from pokemaps_data.validate_maps_gen4 import (
    _validate_dynamic_props,
    _validate_layers,
    _validate_row,
    check_inventory,
    write_inventory,
)


def test_inventory_detects_changed_and_unlisted_assets(tmp_path: Path) -> None:
    asset = tmp_path / "tuile.bin"
    asset.write_bytes(b"pixels")
    write_inventory(tmp_path)
    check_inventory(tmp_path)
    asset.write_bytes(b"autres pixels")
    with pytest.raises(ValueError, match="modifiée sans mise à jour"):
        check_inventory(tmp_path)
    write_inventory(tmp_path)
    (tmp_path / "supplement.bin").write_bytes(b"non inventorie")
    with pytest.raises(ValueError, match="fichiers supplémentaires"):
        check_inventory(tmp_path)


def test_inventory_rejects_paths_outside_the_asset_folder(tmp_path: Path) -> None:
    (tmp_path / "assets.sha256").write_text("0" * 64 + "  ../secret\n", encoding="utf-8")
    with pytest.raises(ValueError, match="entrée d'inventaire DS invalide"):
        check_inventory(tmp_path)


def test_a_child_map_cannot_overflow_its_display(tmp_path: Path) -> None:
    world = {"const": "MONDE", "parent": "", "width": "512", "height": "512"}
    child = {
        "const": "LIEU",
        "name_fr": "Lieu",
        "parent": "MONDE",
        "origin": "",
        "level_count": "0",
        "x": "256",
        "y": "0",
        "width": "512",
        "height": "512",
    }
    with pytest.raises(ValueError, match="région hors de l'assemblage"):
        _validate_row(tmp_path, child, {"MONDE": world})


def test_lower_surface_must_stay_aligned_to_its_base(tmp_path: Path) -> None:
    normal = {"const": "MONDE", "base": None, "bounds": [0, 0, 512, 512]}
    lower = {
        "const": "MONDE_LOWER",
        "base": "MONDE",
        "bounds": [0, 1, 512, 513],
        "replacement": [[0, 0, 512, 512]],
        "level_count": 2,
    }
    with pytest.raises(ValueError, match="niveau inférieur mal aligné"):
        _validate_layers(tmp_path, {"displays": [normal, lower]})


def test_review_uses_generated_tiles_and_refuses_empty_regions(tmp_path: Path) -> None:
    level = tmp_path / "0"
    level.mkdir()
    Image.new("RGBA", (256, 256), (0, 255, 0, 255)).save(level / "0_0.webp", "WEBP", lossless=True)
    thumbnail = region_thumbnail(tmp_path, (256, 256), 1, (0, 0, 128, 128))
    assert thumbnail.getpixel((112, 112)) == (0, 255, 0)
    assert thumbnail.getpixel((0, 0)) == (51, 51, 68)
    with pytest.raises(ValueError, match="région de relecture invalide"):
        region_thumbnail(tmp_path, (256, 256), 1, (0, 0, 0, 10))


def test_dynamic_props_require_known_headers_and_complete_positions(tmp_path: Path) -> None:
    prop = {"header": 35, "model": 300, "position": [256, 160, 256], "rotation": [0, 0, 0], "evidence": "gym.c"}
    path = tmp_path / "dynamic-props.json"
    path.write_text(json.dumps({"props": [prop]}), encoding="utf-8")
    with pytest.raises(ValueError, match="sans en-tête"):
        _validate_dynamic_props(tmp_path, {})
    _validate_dynamic_props(tmp_path, {35: {}})
    prop["position"] = [256, 160]
    path.write_text(json.dumps({"props": [prop]}), encoding="utf-8")
    with pytest.raises(ValueError, match="position ou rotation"):
        _validate_dynamic_props(tmp_path, {35: {}})


def test_review_labels_never_overflow_the_neighboring_card() -> None:
    class Font:
        @staticmethod
        def getlength(value: str) -> int:
            return len(value) * 12

    lines = _label_lines("MAP_HEADER_CANALAVE_CITY_GYM_LOWER_3 — niveau inférieur avec un très long libellé", Font())
    assert len(lines) == 4 and lines[-1].endswith("…")
    assert all(Font.getlength(line) <= 216 for line in lines)
