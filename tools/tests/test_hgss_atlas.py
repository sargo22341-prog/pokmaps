"""Catalogue intégral HGSS et projection Nitro, sans téléchargement ni cache."""

import csv
import json
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data import layers_hgss, preview_johto_hgss, preview_maps_hgss
from pokemaps_data.catalog_maps_hgss import passage_catalog
from pokemaps_data.dynamic_props_hgss import read_dynamic_props
from pokemaps_data.maps_geometry_gen4 import shape_draws
from pokemaps_data.maps_plans_hgss import _plan_name, plan_layout
from pokemaps_data.maps_render_gen4 import _projected_texcoord
from pokemaps_data.maps_render_hgss import HgssRenderer
from pokemaps_data.navigation_hgss import _instructions
from pokemaps_data.pret_gen4_nitro import SbcCommand, _material, read_nsbmd
from pokemaps_data.pret_gen4_source import ByteReader
from pokemaps_data.sources import HGSS_PRET_COMMIT
from pokemaps_data.validate_johto_hgss import _check_safari
from tests.test_gen4_nitro import nsbmd
from tests.test_hgss_johto import _entries, _Repo

_ONE = 4096
_IDENTITY = (_ONE, 0, 0, 0, 0, _ONE, 0, 0, 0, 0, _ONE, 0, 0, 0, 0, _ONE)


def test_atlas_connects_regions_but_keeps_johto_boundary() -> None:
    repo = _Repo()
    repo.warps[1] = (replace(repo.warps[0][0], destination=2),)
    repo.warps[2] = (replace(repo.warps[0][0], destination=0),)
    assert passage_catalog(repo, _entries())[1]["kind"] == "boundary"
    passages = passage_catalog(repo, _entries(), "atlas")
    assert len(passages) == 3 and all(p["kind"] == "fixed" for p in passages)
    assert passages[1]["target_name"] == "Autre région"


def test_kanto_exteriors_keep_native_positions() -> None:
    records = [dict(header=i, plan="kanto-exterieurs", origin_pixels=(i * 100, 0), size=(64, 64)) for i in (0, 3)]
    size, parts = plan_layout(records)
    assert size == (364, 64) and parts[1]["offset"] == (300, 0)
    assert _plan_name(records) == "Kanto — extérieurs"
    assert _plan_name([{**r, "plan": "johto-exterieurs"} for r in records]) == "Johto — extérieurs"


def test_every_nonexcluded_map_has_a_french_name_and_plan() -> None:
    path = Path(__file__).resolve().parents[1] / "data/hgss_maps.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 540
    for row in rows:
        if row["scope"] == "excluded":
            assert row["reason"] and not row["plan"]
        else:
            assert row["name_fr"] and row["plan"] and row["floor"]
    assert sum(r["scope"] == "kanto" for r in rows) == 192
    assert sum(r["scope"] == "special" for r in rows) == 58
    by_header = {int(r["header"]): r for r in rows}
    assert by_header[380]["floor"] == "4f"
    assert by_header[408]["floor"] == "b1f" and by_header[408]["reason"]
    assert by_header[425]["name_fr"] == "Route 11 — poste de la Route 12"


def test_scripted_warps_keep_provenance_and_variable_destination(tmp_path: Path) -> None:
    path = tmp_path / "script.s"
    path.write_text(
        "scene:\n\tWarp MAP_OTHER, 0, 7, 9, DIR_SOUTH\n\tMoveWarp 1, 2, 3\n\tSetDynamicWarp VAR_MAP, 0, 1, 2, 3\n",
        encoding="utf-8",
    )
    fixed, moved, variable = _instructions(path, tmp_path, 1, {"MAP_OTHER": 2})
    assert fixed["destination"] == 2 and fixed["line"] == 2 and fixed["label"] == "scene"
    assert moved["destination_kind"] == "modified_anchor" and "destination" not in moved
    assert variable["destination_kind"] == "variable" and "destination" not in variable


def test_initial_gym_props_cover_platforms_spiders_lift_and_candles() -> None:
    props = read_dynamic_props()
    assert len(props) == 12
    assert {p.header for p in props} == {80, 135, 141, 180}
    assert [(p.model, p.position) for p in props if p.header == 135] == [(111, (248, 32, 328))]
    assert [p.rotation_y for p in props if p.header == 141] == [0, 49152, 0]


def test_effect_matrix_follows_optional_scale_rotation_and_translation() -> None:
    data = bytearray(0x2C)
    struct.pack_into("<3H", data, 0x1E, 0x2001, 32, 16)
    data.extend(struct.pack("<2i2h2i16i", _ONE, _ONE, 0, _ONE, 1, 2, *_IDENTITY))
    material = _material(ByteReader(bytes(data), "effet"), 0, "metal", None, None)
    assert material.effect_matrix == _IDENTITY and material.texture_translation == (1, 2)
    assert _projected_texcoord((_ONE, -_ONE, 0), material) == (32 * 16, 16 * 16)
    with pytest.raises(ValueError):
        _material(ByteReader(bytes(data[:-1]), "effet tronqué"), 0, "metal", None, None)


def test_projection_is_enabled_by_sbc_and_reset_by_next_material() -> None:
    model = read_nsbmd(nsbmd(bytes([1])), "projection").models[0]
    material = replace(model.materials[0], effect_matrix=_IDENTITY)
    commands = (
        SbcCommand(13, 0, (0, 0)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(4, 0, (0,)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(1, 0, ()),
    )
    model = replace(model, materials=(material,), render=commands)
    assert [draw.projected for draw in shape_draws(model)] == [True, False]
    with pytest.raises(ValueError, match="sans matrice"):
        list(shape_draws(replace(model, materials=(replace(material, effect_matrix=()),))))


def test_lower_views_keep_native_witnesses_without_making_rounding_errors_into_floors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = [dict(x=1, z=2, attribute=0, heights=[0, 40 * _ONE]), dict(x=2, z=2, attribute=0, heights=[0, 10])]
    monkeypatch.setattr(layers_hgss, "surface_grid", lambda repo, header: cells)
    monkeypatch.setattr(layers_hgss, "_minimum_geometry_height", lambda renderer, header: 0)
    monkeypatch.setattr(preview_johto_hgss, "_render", lambda renderer, entry, folder, cache: {**entry, "layers": []})
    overlaps, layers, nonvisual = layers_hgss.render_layers(
        HgssRenderer(_Repo()),
        dict(header=0, name_fr="Pont", const="MAP_TEST_0"),
        tmp_path,
        tmp_path,
    )
    assert overlaps == cells
    assert len(layers) == 1 and layers[0]["ceiling_fx32"] == 20 * _ONE
    assert layers[0]["witnesses"] == cells[:1]
    assert nonvisual == []


def test_bdhc_plane_below_all_visible_geometry_is_inventory_not_an_empty_map(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cells = [dict(x=1, z=2, attribute=0, heights=[-95 * _ONE, 16 * _ONE])]
    monkeypatch.setattr(layers_hgss, "surface_grid", lambda repo, header: cells)
    monkeypatch.setattr(layers_hgss, "_minimum_geometry_height", lambda renderer, header: 0)
    monkeypatch.setattr(preview_johto_hgss, "_render", lambda *args: pytest.fail("Aucune géométrie à rendre"))
    overlaps, layers, nonvisual = layers_hgss.render_layers(
        HgssRenderer(_Repo()),
        dict(header=0, name_fr="Grotte", const="MAP_TEST_0"),
        tmp_path,
        tmp_path,
    )
    assert overlaps == cells and layers == []
    assert nonvisual[0]["kind"] == "below_static_geometry" and nonvisual[0]["reason"]
    assert nonvisual[0]["witnesses"] == cells


def test_failure_in_full_atlas_keeps_previous_johto_and_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "preview/hgss-maps"
    target.mkdir(parents=True)
    previous = target / "inventory.json"
    previous.write_text("ancien inventaire", encoding="utf-8")
    monkeypatch.setattr(preview_maps_hgss, "validate_sources", lambda root: {})
    monkeypatch.setattr(preview_maps_hgss, "_version", lambda root, output, version: {"maps": [], "proof": {}})

    def build(root: Path, output: Path, cache: Path, workers: int, scope: str = "johto") -> dict:
        if scope == "atlas":
            raise ValueError("Kanto : rendu impossible")
        return {}

    monkeypatch.setattr(preview_johto_hgss, "build_johto", build)
    with pytest.raises(ValueError, match="Kanto : rendu impossible"):
        preview_maps_hgss.build_hgss_maps(tmp_path / "cache", target.parent, 1)
    assert previous.read_text(encoding="utf-8") == "ancien inventaire"


def test_safari_rejects_a_configuration_that_repeats_the_same_habitat() -> None:
    safari = dict(
        runtime_header=357,
        matrix=212,
        templates=[dict(area=i, header=343 + i, block=652 + i) for i in range(12)],
        slots=[dict(column=x + 1, row=z + 1) for z in range(2) for x in range(3)],
        initial_sets=[list(range(6)) for _ in range(10)],
    )
    catalog = dict(safari=safari, maps=[dict(header=i) for i in (*range(343, 355), 357)])
    _check_safari(catalog)
    safari["initial_sets"][0] = [0] * 6
    with pytest.raises(ValueError, match="Safari HGSS"):
        _check_safari(catalog)


def test_catalog_recipe_changes_when_navigation_or_view_selection_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in preview_johto_hgss._CATALOG_MODULES:
        (tmp_path / name).write_text("source initiale\n", encoding="utf-8")
    monkeypatch.setattr(preview_johto_hgss, "__file__", str(tmp_path / "preview_johto_hgss.py"))
    initial = preview_johto_hgss._catalog_recipe()
    (tmp_path / "navigation_hgss.py").write_text("navigation modifiée\n", encoding="utf-8")
    changed = preview_johto_hgss._catalog_recipe()
    assert initial != changed
    (tmp_path / "layers_hgss.py").write_text("sélection modifiée\n", encoding="utf-8")
    assert changed != preview_johto_hgss._catalog_recipe()


def test_versioned_review_proof_covers_current_catalog_and_generator() -> None:
    root = Path(__file__).resolve().parents[2]
    report = json.loads((root / "docs/generations/cartes-hgss-atlas-preuve.json").read_text(encoding="utf-8"))
    with (root / "tools/data/hgss_maps.csv").open(encoding="utf-8", newline="") as handle:
        entries = [row for row in csv.DictReader(handle) if row["scope"] != "excluded"]
    assert report["commit"] == HGSS_PRET_COMMIT
    assert report["catalog_recipe"] == preview_johto_hgss._catalog_recipe()
    assert set(report["pixels_sha256"]) == {row["header"] for row in entries}
    assert report["plans"] == len({row["plan"] for row in entries})
    assert report["layers"] == len(report["layer_pixels_sha256"])
    assert report["review_cards"] == len(entries) + report["plans"] + report["layers"] + 2
    assert report["review_coverage"] == {"lieu": 496, "coupe": 196, "plan": 224, "plan-detail": 2}
