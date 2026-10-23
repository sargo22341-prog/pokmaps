"""Régressions des plans HGSS distribués et des terrains exclus de la carte."""

import json
import sqlite3
from pathlib import Path

from PIL import Image

from pokemaps_data.layers_application_hgss import actor_layer, surface_map
from pokemaps_data.map_spots import TerrainKey, read_spots
from pokemaps_data.maps import GameMapData, MapRow
from pokemaps_data.maps_export_hgss import _native_map, _spots
from pokemaps_data.origins_hgss import assign_origins
from pokemaps_data.plans_application_hgss import application_catalog


def test_separate_houses_keep_local_door_coordinates() -> None:
    records = [
        dict(header=h, const=f"MAP_HOUSE_{h}", plan="town-base", name_fr=f"Maison {h}", floor="base", size=[128, 128])
        for h in (1, 2, 3)
    ]
    source = dict(
        maps=records,
        plans=[dict(id="town-base", parts=[dict(header=h, offset=[h * 384, 0]) for h in (1, 2, 3)])],
        passages=[dict(source=1, destination=2, source_pixel=[400, 32], target_pixel=[800, 48])],
    )
    result = application_catalog(source, dict.fromkeys((1, 2, 3), "MAP_TYPE_INTERIOR"))
    assert len(result["plans"]) == 2
    assert result["maps"][2]["plan"] == "house-3-plan"
    assert result["plans"][1]["size"] == (128, 128)
    assert not result["plans"][1]["standalone"]
    passage = result["passages"][0]
    assert passage["source_pixel"] == [16, 32]
    assert passage["target_pixel"] == [416, 48]
    assert source["passages"][0]["source_pixel"] == [400, 32]


def test_an_outdoor_access_does_not_merge_separate_buildings() -> None:
    records = [
        dict(header=h, const=f"MAP_ROOM_{h}", plan="facility-base", name_fr=f"Salle {h}", floor="base", size=[128, 128])
        for h in (1, 2, 3)
    ]
    source = dict(
        maps=records,
        plans=[dict(id="facility-base", parts=[dict(header=h, offset=[0, 0]) for h in (1, 2, 3)])],
        passages=[dict(source=1, destination=2), dict(source=1, destination=3)],
    )
    result = application_catalog(source, {1: "MAP_TYPE_CITY_TOWN", 2: "MAP_TYPE_INTERIOR", 3: "MAP_TYPE_INTERIOR"})
    assert len(result["plans"]) == 3


def test_a_house_reached_from_the_world_needs_no_parent_plan() -> None:
    source = dict(
        maps=[
            dict(header=1, const="MAP_TOWN", plan="johto-exterieurs", name_fr="Ville", size=[128, 128]),
            dict(header=2, const="MAP_HOUSE", plan="town-base", name_fr="Maison", size=[128, 128]),
        ],
        plans=[
            dict(id="johto-exterieurs", parts=[dict(header=1, offset=[0, 0])]),
            dict(id="town-base", parts=[dict(header=2, offset=[384, 0])]),
        ],
        passages=[dict(source=1, destination=2)],
    )
    result = application_catalog(source, {1: "MAP_TYPE_CITY_TOWN", 2: "MAP_TYPE_INTERIOR"})
    assert result["plans"][1]["id"] == "MAP_HOUSE"
    assert result["plans"][1]["standalone"]


def test_an_isolated_template_keeps_a_native_child_as_its_origin(tmp_path: Path) -> None:
    record = dict(
        header=343, const="MAP_SAFARI_ZONE_01", plan="safari-zone-01-plan", name_fr="Safari — plaine", size=[128, 128]
    )
    plan = dict(standalone=False, level_count=1)
    child = _native_map(tmp_path, tmp_path, record, plan, record["plan"], (0, 0))
    parent = MapRow(record["plan"], 540, record["name_fr"], None, 0, 0, 128, 128, 1)
    assign_origins([parent, child], dict(maps=[record], passages=[], script_navigation=[]))
    assert child.parent == parent.const and child.level_count == 0
    assert parent.origin == child.const and parent.origin != parent.const


def test_excluded_water_does_not_export_rejected_automatic_candidates() -> None:
    data = GameMapData([], [], [], [])
    placement = dict(
        coverage=[dict(header=34, kind="water", reason="Eau masquée")],
        catalog=dict(maps=[dict(header=34, terrain=dict(water=[[8, 8]], grass=[[24, 24]]))]),
    )
    _spots(data, placement, {34: dict(const="MAP_ROUTE_30")}, {"route-30": (100, 200)})
    assert [(r.kind, r.x, r.y) for r in data.spots] == [("grass", 124, 224)]
    assert data.terrain[("route-30", "water")] == frozenset({(108, 208)})


def test_world_geometry_does_not_create_lower_worlds() -> None:
    for plan in ("johto-exterieurs", "kanto-exterieurs"):
        record = dict(plan=plan, const="MAP_ROUTE_30", layers=[dict(ceiling_fx32=100)])
        assert surface_map(record, 0) == "MAP_ROUTE_30"
        assert actor_layer(record, 100) == "MAP_ROUTE_30"


def test_distributed_houses_are_individual_maps(db: sqlite3.Connection) -> None:
    rows = db.execute("""SELECT identifier, parent_map_id, level_count FROM map
                         WHERE version_group_id=10 AND identifier IN
                         ('cherrygrove-pokemart', 'cherrygrove-southwest-house',
                          'cherrygrove-guide-gent-house', 'cherrygrove-southeast-house')""").fetchall()
    assert len(rows) == 4
    assert all(parent is None and levels > 0 for _, parent, levels in rows)
    assert db.execute("""SELECT count(*) FROM map WHERE version_group_id=10
                         AND (identifier LIKE 'johto-lower%' OR identifier LIKE 'kanto-lower%')""").fetchone() == (0,)


def test_all_distributed_wild_points_follow_editorial_terrain(assets: Path, db: sqlite3.Connection) -> None:
    root = assets / "maps/heartgold-soulsilver"
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    native = {r["const"]: r for r in catalog["source_catalog"]["maps"]}
    offsets = json.loads((root / "assemblies.json").read_text(encoding="utf-8"))
    curated = read_spots()
    exclusions = Path(__file__).parents[1] / "data/hgss_spot_exclusions.csv"
    import csv

    with exclusions.open(encoding="utf-8", newline="") as handle:
        excluded = {(int(r["header"]), r["kind"]) for r in csv.DictReader(handle)}
    rows = db.execute("""SELECT m.identifier, s.kind, s.x, s.y FROM map_spot s JOIN map m ON m.id=s.map_id
                         WHERE m.version_group_id=10""").fetchall()
    assert rows
    for name, kind, x, y in rows:
        const = "MAP_" + name.upper().replace("-", "_")
        assert (native[const]["header"], kind) not in excluded
        dx, dy = offsets[const]["offset"]
        assert (x - dx, y - dy) in curated[TerrainKey("heartgold-soulsilver", name, kind)]


def test_water_markers_are_on_blue_water_in_the_distributed_tiles(assets: Path, db: sqlite3.Connection) -> None:
    rows = db.execute("""SELECT coalesce(p.identifier,m.identifier),
                                coalesce(p.level_count,m.level_count),s.x,s.y
                         FROM map_spot s JOIN map m ON m.id=s.map_id
                         LEFT JOIN map p ON p.id=m.parent_map_id
                         WHERE m.version_group_id=10 AND s.kind='water'""").fetchall()
    assert rows
    for name, levels, x, y in rows:
        path = assets / "maps/heartgold-soulsilver" / name / str(levels - 1) / f"{y // 256}_{x // 256}.webp"
        with Image.open(path) as image:
            red, green, blue, alpha = image.convert("RGBA").getpixel((x % 256, y % 256))
        assert alpha == 255 and blue - red >= 24 and blue >= green, (name, x, y)
