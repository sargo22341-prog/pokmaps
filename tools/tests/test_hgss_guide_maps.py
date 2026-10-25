"""Le guide HGSS conserve les étages réels, les accès et un monde commun."""

import json
import re
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data import passages_guide_hgss
from pokemaps_data.layers_application_hgss import actor_layer, surface_map
from pokemaps_data.plans_application_hgss import application_catalog


def test_technical_surfaces_share_the_upper_map() -> None:
    record = dict(const="MAP_CERULEAN_CAVE_1F", plan="cave", layers=[dict(ceiling_fx32=100)])
    assert surface_map(record, 0) == record["const"]
    assert surface_map(record, 200) == record["const"]
    assert actor_layer(record, 100) == record["const"]
    with pytest.raises(ValueError, match="coupe inconnue"):
        actor_layer(record, 200)


def test_world_merge_translates_both_ends_without_changing_source() -> None:
    records = [
        dict(header=1, const="MAP_A", plan="johto-exterieurs", origin_pixels=[0, 0], size=[256, 256]),
        dict(header=2, const="MAP_B", plan="kanto-exterieurs", origin_pixels=[512, 0], size=[256, 256]),
    ]
    source = dict(
        maps=records,
        plans=[dict(id=r["plan"], parts=[dict(header=r["header"], offset=[0, 0])]) for r in records],
        passages=[dict(source=1, destination=2, source_pixel=[8, 24], target_pixel=[40, 56])],
    )
    result = application_catalog(source, {1: "OUTSIDE", 2: "OUTSIDE"})
    assert len(result["plans"]) == 1
    assert result["plans"][0]["size"] == (768, 256)
    assert result["passages"][0]["target_pixel"] == [552, 56]
    assert result["passages"][0]["source_pixel"] == [8, 24]
    assert records[1]["plan"] == "kanto-exterieurs"
    assert source["passages"][0]["target_pixel"] == [40, 56]


def test_unknown_or_repeated_excluded_passage_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(passages_guide_hgss, "DATA_DIR", tmp_path)
    path = tmp_path / "hgss_guide_passages.csv"
    path.write_text("source,index,reason\n448,4,Variante inactive\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exclusion de passage invalide"):
        passages_guide_hgss.excluded_passages(dict(passages=[]))
    catalog = dict(passages=[dict(source=448, index=4)])
    assert passages_guide_hgss.excluded_passages(catalog) == {(448, 4)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write("448,4,Variante inactive\n")
    with pytest.raises(ValueError, match="exclusion de passage invalide"):
        passages_guide_hgss.excluded_passages(catalog)


def test_distributed_guide_has_no_technical_floors(db: sqlite3.Connection, assets: Path) -> None:
    count = db.execute("""SELECT count(*) FROM map WHERE version_group_id=10
                          AND (identifier GLOB '*-lower' OR identifier GLOB '*-lower-[0-9]*')""").fetchone()
    assert count == (0,)
    rows = db.execute("SELECT identifier FROM map WHERE version_group_id=10 AND identifier LIKE 'cerulean-cave-%'")
    assert {row[0] for row in rows} == {"cerulean-cave-1f", "cerulean-cave-2f", "cerulean-cave-b1f"}
    folder = assets / "maps/heartgold-soulsilver"
    assert not any(re.fullmatch(r".+-lower(?:-[1-9][0-9]*)?", path.name) for path in folder.iterdir())
    assert (folder / "mount-silver-cave-lower-mountainside").is_dir()


def test_moon_square_and_pal_park_are_accessible(assets: Path) -> None:
    catalog = json.loads((assets / "maps/heartgold-soulsilver/catalog.json").read_text(encoding="utf-8"))
    warps = catalog["passages"]
    entrance = [w for w in warps if w["map_const"] == "MAP_MOUNT_MOON_SQUARE_ENTRANCE"]
    assert len(entrance) == 4
    assert all(w["target"] != "MAP_MOUNT_MOON_SQUARE_CLEFAIRY_EVENT" for w in entrance)
    assert any(w["map_const"] == "MAP_MOUNT_MOON_SQUARE" and w["target"] == "MAP_MOUNT_MOON_SQUARE_SHOP" for w in warps)
    assert any(w["map_const"] == "MAP_FUCHSIA_PAL_PARK_ENTRANCE" and w["target"] == "MAP_PAL_PARK" for w in warps)


def test_mount_silver_and_league_share_the_world_with_both_regions(db: sqlite3.Connection) -> None:
    names = ("new-bark", "pallet", "mount-silver", "route-28", "indigo-plateau")
    parents = []
    for name in names:
        row = db.execute("SELECT parent_map_id FROM map WHERE version_group_id=10 AND identifier=?", (name,)).fetchone()
        assert row is not None
        parents.append(row[0])
    assert len(set(parents)) == 1 and parents[0] is not None
