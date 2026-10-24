"""Atlas Safari distribué : disposition, coordonnées sauvages et accès depuis l'entrée."""

import json
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.map_coordinates import editor_offsets
from pokemaps_data.safari_atlas_hgss import _parts, validate_atlas


def test_layout_crops_margins_and_places_the_entrance_below_the_second_column(tmp_path: Path) -> None:
    rows = []
    names = [f"MAP_SAFARI_ZONE_{number:02}" for number in range(1, 13)] + ["MAP_SAFARI_ZONE_ENTRANCE_EXTERIOR"]
    for name in names:
        folder = tmp_path / name.removeprefix("MAP_").lower().replace("_", "-") / "0"
        folder.mkdir(parents=True)
        with Image.new("RGBA", (256, 256)) as image:
            image.paste((32, 160, 64, 255), (16, 24, 80, 88))
            image.save(folder / "0_0.webp", lossless=True)
        rows.append(dict(const=name, parent=None, width=256, height=256, level_count=1))
    parts, size = _parts(tmp_path, rows)
    assert size == (464, 224)
    assert [part.const for part in parts[:6]] == [names[number - 1] for number in (1, 2, 3, 7, 8, 9)]
    assert [(part.x, part.y) for part in parts[:6]] == [(number * 80, 0) for number in range(6)]
    assert [(part.x, part.y) for part in parts[6:12]] == [(number * 80, 80) for number in range(6)]
    assert parts[-1].x == 80 and parts[-1].y == 160
    assert parts[-1].shift == (64, 136)
    assert all(part.crop == (16, 24, 80, 88) for part in parts)


def test_distributed_atlas_has_thirteen_selectable_regions(assets: Path, db: sqlite3.Connection) -> None:
    validate_atlas(assets)
    offsets = editor_offsets(assets / "maps")
    assert offsets[("heartgold-soulsilver", "safari-zone-01")][0] < 0
    atlas = db.execute("SELECT id,width,height FROM map WHERE identifier='safari-atlas'").fetchone()
    assert atlas is not None
    regions = db.execute(
        "SELECT identifier,x,y,width,height,level_count FROM map WHERE parent_map_id=?", (atlas[0],)
    ).fetchall()
    assert len(regions) == 13
    assert all(
        levels == 0 and 0 <= x < x + w <= atlas[1] and 0 <= y < y + h <= atlas[2] for _, x, y, w, h, levels in regions
    )
    entrances = db.execute(
        """SELECT count(*) FROM map_warp w JOIN map m ON m.id=w.target_map_id
           WHERE m.identifier='safari-zone-entrance-exterior' AND m.parent_map_id=?""",
        (atlas[0],),
    ).fetchone()[0]
    assert entrances > 0
    points_outside = db.execute(
        """SELECT count(*) FROM map_spot s JOIN map m ON m.id=s.map_id WHERE m.parent_map_id=?
           AND (s.x<m.x OR s.x>=m.x+m.width OR s.y<m.y OR s.y>=m.y+m.height)""",
        (atlas[0],),
    ).fetchone()[0]
    assert points_outside == 0


def test_atlas_validation_rejects_overlapping_habitats(assets: Path, tmp_path: Path) -> None:
    folder = tmp_path / "maps/heartgold-soulsilver"
    folder.mkdir(parents=True)
    data = json.loads((assets / "maps/heartgold-soulsilver/catalog.json").read_text(encoding="utf-8"))
    first, second = data["safari_atlas"][:2]
    second["x"], second["y"] = first["x"], first["y"]
    row = next(row for row in data["maps"] if row["const"] == second["const"])
    row["x"], row["y"] = first["x"], first["y"]
    (folder / "catalog.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="habitats superposés"):
        validate_atlas(tmp_path)
