"""Placement HGSS : projection, terrains, retouches et absence de trous silencieux."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from pokemaps_data import preview_placement_hgss as preview
from pokemaps_data import terrain_hgss as terrain
from pokemaps_data import visibility_hgss as visibility
from pokemaps_data.map_spots import TerrainKey, read_spots, write_spots
from pokemaps_data.maps_raster_gen4 import ONE, RasterMaterial, RasterVertex
from pokemaps_data.placement_hgss import (
    FAMILY,
    coverage,
    placement_catalog,
    points_digest,
    read_placement_json,
    spread_pixels,
    visible_cells,
)
from pokemaps_data.preview_placement_hgss import exceptions, validate_coverage, validate_placement_sources
from pokemaps_data.sources import HGSS_PRET_COMMIT
from pokemaps_data.terrain_hgss import project_cell, terrain_kind, tile_flags
from spot_editor.catalog import Family
from spot_editor.hgss import HgssCatalog

TOOLS = Path(__file__).resolve().parents[1]
PROOF = TOOLS.parent / "docs/generations/placements-hgss-preuve.json"


def test_pixel_spacing_is_measured_in_pixels_instead_of_native_cells() -> None:
    points = [(x * 16, 19) for x in range(20)]
    result = spread_pixels(points, "test")
    assert result == spread_pixels(list(reversed(points)), "test")
    assert len(result) > 1
    assert all((x - a) ** 2 + (y - b) ** 2 >= 32**2 for i, (x, y) in enumerate(result) for a, b in result[i + 1 :])


def test_hgss_flags_keep_fishing_distinct_from_surf_and_block_walking_collisions() -> None:
    flags = {2: "ENCOUNTER", 8: "ENCOUNTER", 17: "SURFABLE", 21: "SURFABLE_ENCOUNTER"}
    assert terrain_kind(2, False, flags, {"walk"}) == "grass"
    assert terrain_kind(8, False, flags, {"walk"}) == "floor"
    assert terrain_kind(8, True, flags, {"walk"}) is None
    assert terrain_kind(17, False, flags, {"surf"}) is None
    assert terrain_kind(17, False, flags, {"old-rod"}) == "water"
    assert terrain_kind(21, False, flags, {"surf"}) == "water"


def test_missing_height_never_becomes_an_arbitrary_flat_point() -> None:
    block = SimpleNamespace(bdhc=None)
    point, reason = project_cell(block, (3, 4), 0, 4096, dict(origin_pixels=[0, 0], size=[512, 512]))
    assert point is None and "BDHC" in reason


def test_water_surface_and_bottom_do_not_remove_the_whole_pond(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(terrain, "heights", lambda *_args: (0, 16 * ONE))
    block = SimpleNamespace(bdhc=object())
    record = dict(origin_pixels=[0, 0], size=[512, 512])
    assert project_cell(block, (3, 4), 0, ONE, record)[0] is None
    water, reason = project_cell(block, (3, 4), 0, ONE, record, allow_levels=True)
    assert not reason and water is not None
    assert water.point == (56, 56) and water.depth == 88 * ONE


def test_points_on_transparent_pixels_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "map.png"
    image = Image.new("RGBA", (32, 32))
    image.putpixel((8, 8), (0, 255, 0, 255))
    image.putpixel((24, 8), (0, 0, 0, 255))
    image.save(path)
    rejected = []
    assert visible_cells(path, {"grass": [(8, 8), (24, 8)]}, rejected) == {"grass": [(8, 8)]}
    assert rejected[0]["point"] == (24, 8)


def test_native_water_candidates_on_trees_cannot_be_replacement_spots(tmp_path: Path) -> None:
    path = tmp_path / "water.png"
    image = Image.new("RGBA", (64, 64), (82, 115, 41, 255))
    image.putpixel((40, 40), (20, 150, 220, 255))
    image.save(path)
    rejected = []
    assert visible_cells(path, {"water": [(24, 24), (40, 40)]}, rejected) == {"water": [(40, 40)]}
    assert rejected[0]["point"] == (24, 24)


def test_editor_snaps_to_projected_center_instead_of_flat_grid() -> None:
    catalog = object.__new__(HgssCatalog)
    catalog.records = {"route-29": dict(terrain={"grass": [[24, 26], [56, 42]]})}
    family = Family(FAMILY, "HGSS", (FAMILY,))
    assert catalog.snap(family, "route-29", "grass", 25, 25) == (24, 26)
    assert catalog.snap(family, "route-29", "grass", 100, 100) is None
    assert catalog.snap(family, "route-29", "water", 24, 26) is None


def test_explained_absence_never_falls_back_to_automatic_points_in_editor() -> None:
    catalog = object.__new__(HgssCatalog)
    catalog.records = {
        "route-6": dict(
            terrain={"water": [[24, 26]], "grass": [[56, 42]]}, generated={"water": [[24, 26]], "grass": [[56, 42]]}
        )
    }
    catalog.excluded = {("route-6", "water")}
    family = Family(FAMILY, "HGSS", (FAMILY,))
    generated = catalog.generated_spots(SimpleNamespace(identifier="route-6"))
    assert catalog.kinds(family, "route-6") == frozenset({"grass"})
    assert generated["water"] == frozenset()
    assert generated["grass"] == frozenset({(56, 42)})


def test_native_water_hidden_by_a_cliff_is_not_a_visible_water_marker() -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(visibility, "camera_cotangent", lambda _root, _header: ONE)
        header = SimpleNamespace(index=1)
        repo = SimpleNamespace(headers={1: header}, root=Path("."), blocks=lambda _h: [(0, 0, 0, 0)])
        material = RasterMaterial(None, 31, 3)
        vertices = tuple(
            RasterVertex((x * ONE, 16 * ONE, z * ONE), (0, 0), (31, 31, 31)) for x, z in ((0, 0), (64, 0), (0, 64))
        )
        renderer = SimpleNamespace(repo=repo, triangles=lambda *_args: [(vertices, material)])
        rejected = []
        record = dict(header=1, origin_pixels=[0, 0])
        assert visibility.visible_surfaces(renderer, record, {"water": [(8, 8)]}, {(8, 8): 8 * ONE}, rejected) == {}
        assert "incompatible" in rejected[0]["reason"]
        assert visibility.visible_surfaces(renderer, record, {"floor": [(8, 8)]}, {(8, 8): 40 * ONE}, [])


def test_coverage_rejects_outside_points_and_unknown_maps(tmp_path: Path) -> None:
    catalog = dict(
        maps=[
            dict(
                header=33,
                identifier="route-29",
                scope="johto",
                lines=[dict(method="walk")],
                terrain={"grass": [[24, 26]]},
            )
        ]
    )
    path = tmp_path / "map_spots.csv"
    key = TerrainKey(FAMILY, "route-29", "grass")
    write_spots({key: {(24, 24)}}, path)
    with pytest.raises(ValueError, match="hors terrain"):
        coverage(catalog, path)
    write_spots({TerrainKey(FAMILY, "absent", "grass"): {(24, 26)}}, path)
    with pytest.raises(ValueError, match="sans terrain"):
        coverage(catalog, path)


def test_no_coverage_requires_an_explicit_reason_and_stale_exclusions_fail() -> None:
    row = dict(header=486, kind="floor", points=0)
    with pytest.raises(ValueError, match="sans couverture"):
        validate_coverage([row], {})
    assert validate_coverage([row], {(486, "floor"): "Pas de surface BDHC"})[0]["reason"]
    with pytest.raises(ValueError, match="inutilisées"):
        validate_coverage([row | dict(points=1)], {(486, "floor"): "Ancienne exception"})


def test_snapshot_rejects_modified_output_but_editor_can_open_invalid_curation(tmp_path: Path) -> None:
    target = tmp_path / "placement.json"
    data = dict(
        commit=HGSS_PRET_COMMIT,
        sources={},
        recipe={},
        native_sources=read_placement_json(preview.CONTRACT),
        water_regions_sha256=preview.digest(preview.DATA / "hgss_water_regions.csv"),
        catalog={"maps": []},
        coverage=[],
    )
    target.write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "inventory.json").write_text(json.dumps({"placement.json": preview.digest(target)}), encoding="utf-8")
    assert preview.check_placement(tmp_path, validate_spots=False)["coverage"] == []
    target.write_text(json.dumps(data | {"changed": True}), encoding="utf-8")
    with pytest.raises(ValueError, match="modifié"):
        preview.check_placement(tmp_path, validate_spots=False)


def test_committed_coverage_matches_every_curated_point_without_cache() -> None:
    proof = read_placement_json(PROOF)
    spots = read_spots()
    actual = {key for key in spots if key.family == FAMILY}
    expected = set()
    for row in proof["coverage"]:
        key = TerrainKey(FAMILY, row["map"], row["kind"])
        points = spots.get(key, frozenset())
        assert len(points) == row["points"]
        assert points_digest(points) == row["points_sha256"]
        if points:
            expected.add(key)
    assert actual == expected
    assert len({r["header"] for r in proof["coverage"]}) == 151
    assert {r["scope"] for r in proof["coverage"]} == {"johto", "kanto", "special"}
    validate_coverage(proof["coverage"], exceptions())


@pytest.mark.pipeline
def test_native_hgss_terrain_covers_both_regions_and_all_special_templates() -> None:
    root = TOOLS / ".cache/hgss-qualification"
    preview = TOOLS / "build/preview"
    validate_placement_sources(root)
    flags = tile_flags(root)
    assert flags[2] == "ENCOUNTER" and flags[21] == "SURFABLE_ENCOUNTER"
    catalog = placement_catalog(
        root, preview / "hgss-maps", read_placement_json(preview / "hgss-encounters/encounters.json")
    )
    rows = validate_coverage(coverage(catalog, TOOLS / "data/map_spots.csv"), exceptions())
    assert rows == read_placement_json(PROOF)["coverage"]
    assert len(catalog["maps"]) == 151 and not catalog["excluded"]
    assert {r["header"] for r in catalog["maps"]} >= set(range(343, 355)) | {96, 487}
    spots = read_spots()
    for record in catalog["maps"]:
        with Image.open(preview / "hgss-maps/atlas" / record["image"]) as image:
            pixels = image.convert("RGBA")
            for points in record["terrain"].values():
                assert all(pixels.getpixel(tuple(p))[3] and max(pixels.getpixel(tuple(p))[:3]) > 8 for p in points)
            # La curation aquatique a été relue sur l'eau bleue/cyan, pas sur les props ou les berges.
            for point in spots.get(TerrainKey(FAMILY, record["identifier"], "water"), ()):
                red, green, blue, _ = pixels.getpixel(point)
                assert blue - red >= 24 and blue >= green, (record["const"], point)
