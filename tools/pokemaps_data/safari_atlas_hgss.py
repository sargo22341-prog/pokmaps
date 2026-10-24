"""Atlas éditorial du Safari : douze habitats côte à côte, entrée en dessous, sans agencement de jeu inventé."""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from .maps_layout import identifier
from .maps_plans_hgss import _paste_tiles, _reduce_tiles
from .maps_render import level_count
from .validate_maps_gen4 import write_inventory

_ATLAS = "safari-atlas"
_NUMBER = 991
_ORDER = (1, 2, 3, 7, 8, 9, 4, 5, 6, 10, 11, 12)
_ENTRANCE = "MAP_SAFARI_ZONE_ENTRANCE_EXTERIOR"


@dataclass(frozen=True)
class _Part:
    const: str
    source: str
    levels: int
    crop: tuple[int, int, int, int]
    x: int
    y: int

    @property
    def shift(self) -> tuple[int, int]:
        return self.x - self.crop[0], self.y - self.crop[1]


def _read_image(folder: Path, row: dict) -> Image.Image:
    if not 1 <= row["level_count"] <= 8 or max(row["width"], row["height"]) > 2048:
        raise ValueError(f"Safari : dimensions ou niveaux invalides pour {row['const']}")
    result = Image.new("RGBA", (row["width"], row["height"]))
    paths = sorted((folder / identifier(row["const"]) / str(row["level_count"] - 1)).glob("*.webp"))
    if not 1 <= len(paths) <= 64:
        raise ValueError(f"Safari : tuiles absentes ou trop nombreuses pour {row['const']}")
    for path in paths:
        y, x = map(int, path.stem.split("_"))
        with Image.open(path) as tile:
            result.paste(tile.convert("RGBA"), (x * 256, y * 256))
    return result


def _parts(folder: Path, rows: list[dict]) -> tuple[list[_Part], tuple[int, int]]:
    lookup = {row["const"]: row for row in rows}
    sources = []
    crops = []
    constants = [f"MAP_SAFARI_ZONE_{number:02}" for number in _ORDER] + [_ENTRANCE]
    for const in constants:
        native = lookup[const]
        source = lookup[native["parent"]] if native["parent"] else native
        image = _read_image(folder, source)
        crop = image.getbbox()
        image.close()
        if crop is None:
            raise ValueError(f"Safari : image vide pour {const}")
        sources.append(source)
        crops.append(crop)
    cell_width = max(crop[2] - crop[0] for crop in crops) + 16
    cell_height = max(crop[3] - crop[1] for crop in crops) + 16
    parts = []
    for index, (const, source, crop) in enumerate(zip(constants, sources, crops, strict=True)):
        column, row = (index % 6, index // 6) if index < 12 else (1, 2)
        parts.append(_Part(const, source["const"], source["level_count"], crop, column * cell_width, row * cell_height))
    return parts, (cell_width * 6 - 16, cell_height * 3 - 16)


def build_atlas(assets: Path) -> None:
    folder = assets / "maps/heartgold-soulsilver"
    path = folder / "catalog.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if "safari_atlas" in catalog:
        validate_atlas(assets)
        _update_recipe(assets)
        write_inventory(folder)
        return
    parts, size = _parts(folder, catalog["maps"])
    atlas = dict(
        const=_ATLAS,
        number=_NUMBER,
        name_fr="Parc Safari",
        parent=None,
        x=0,
        y=0,
        width=size[0],
        height=size[1],
        level_count=level_count(*size),
        is_world=False,
        origin="MAP_SAFARI_ZONE_GATE",
        start=None,
        version=None,
    )
    if any(row["number"] == _NUMBER for row in catalog["maps"]):
        raise ValueError("Safari : identifiant de l'atlas déjà attribué")
    _write_tiles(folder, catalog["maps"], parts, atlas)
    _update_catalog(catalog, parts, atlas)
    _write_json(path, catalog)
    _update_placements(folder, parts)
    with closing(sqlite3.connect(assets / "database/pokedex.db")) as connection, connection:
        _update_database(connection, parts, atlas)
    _update_recipe(assets)
    write_inventory(folder)
    validate_atlas(assets)


def _update_recipe(assets: Path) -> None:
    from .application_hgss import export_recipe

    path = assets / "hgss.json"
    if path.is_file():
        content = json.loads(path.read_text(encoding="utf-8"))
        content["application_recipe"] = export_recipe()
        _write_json(path, content)


def _write_tiles(folder: Path, rows: list[dict], parts: list[_Part], atlas: dict) -> None:
    output = folder / _ATLAS
    if output.exists():
        raise ValueError(f"Safari : dossier de génération déjà présent : {output}")
    lookup = {row["const"]: row for row in rows}
    for part in parts:
        with _read_image(folder, lookup[part.source]) as image:
            _paste_tiles(image.crop(part.crop), (part.x, part.y), output / str(atlas["level_count"] - 1))
    for level in range(atlas["level_count"] - 2, -1, -1):
        _reduce_tiles(output / str(level + 1), output / str(level))


def _update_catalog(catalog: dict, parts: list[_Part], atlas: dict) -> None:
    lookup = {row["const"]: row for row in catalog["maps"]}
    shifts = {part.const: part.shift for part in parts}
    for part in parts:
        row = lookup[part.const]
        row.update(
            parent=_ATLAS,
            x=part.x,
            y=part.y,
            width=part.crop[2] - part.crop[0],
            height=part.crop[3] - part.crop[1],
            level_count=0,
        )
    for warp in catalog["passages"]:
        for field, x, y in (("map_const", "x", "y"), ("target", "target_x", "target_y")):
            if warp[field] in shifts and warp[x] is not None:
                dx, dy = shifts[warp[field]]
                warp[x] += dx
                warp[y] += dy
    catalog["maps"].append(atlas)
    catalog["safari_atlas"] = [asdict(part) for part in parts]


def _update_placements(folder: Path, parts: list[_Part]) -> None:
    assemblies = json.loads((folder / "assemblies.json").read_text(encoding="utf-8"))
    terrain = json.loads((folder / "terrain.json").read_text(encoding="utf-8"))
    for part in parts:
        dx, dy = part.shift
        offset = assemblies[part.const]["offset"]
        assemblies[part.const]["offset"] = [offset[0] + dx, offset[1] + dy]
        for kind, points in terrain[identifier(part.const)]["terrain"].items():
            terrain[identifier(part.const)]["terrain"][kind] = [[x + dx, y + dy] for x, y in points]
    _write_json(folder / "assemblies.json", assemblies)
    _write_json(folder / "terrain.json", terrain)


def _update_database(connection: sqlite3.Connection, parts: list[_Part], atlas: dict) -> None:
    atlas_id = 10_000 + _NUMBER
    origin = connection.execute(
        "SELECT id FROM map WHERE version_group_id=10 AND identifier='safari-zone-gate'"
    ).fetchone()[0]
    connection.execute(
        "INSERT INTO map VALUES (?,10,?,?,NULL,0,0,?,?,?,0,?,?,NULL,NULL,0)",
        (atlas_id, _ATLAS, atlas["name_fr"], atlas["width"], atlas["height"], atlas["level_count"], origin, None),
    )
    for part in parts:
        map_id = connection.execute(
            "SELECT id FROM map WHERE version_group_id=10 AND identifier=?", (identifier(part.const),)
        ).fetchone()[0]
        dx, dy = part.shift
        connection.execute(
            "UPDATE map SET parent_map_id=?,x=?,y=?,width=?,height=?,level_count=0 WHERE id=?",
            (atlas_id, part.x, part.y, part.crop[2] - part.crop[0], part.crop[3] - part.crop[1], map_id),
        )
        for table in ("map_spot", "map_object", "map_warp"):
            connection.execute(f"UPDATE {table} SET x=x+?,y=y+? WHERE map_id=?", (dx, dy, map_id))
        connection.execute(
            "UPDATE map_warp SET target_x=target_x+?,target_y=target_y+? WHERE target_map_id=?", (dx, dy, map_id)
        )


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def validate_atlas(assets: Path) -> None:
    folder = assets / "maps/heartgold-soulsilver"
    catalog = json.loads((folder / "catalog.json").read_text(encoding="utf-8"))
    parts = catalog.get("safari_atlas", [])
    expected = [f"MAP_SAFARI_ZONE_{number:02}" for number in _ORDER] + [_ENTRANCE]
    if [part["const"] for part in parts] != expected:
        raise ValueError("Safari : les douze habitats et l'entrée sont requis dans l'atlas")
    rows = {row["const"]: row for row in catalog["maps"]}
    atlas = rows[_ATLAS]
    rectangles = []
    for part in parts:
        row = rows[part["const"]]
        if row["parent"] != _ATLAS or row["level_count"] != 0 or (row["x"], row["y"]) != (part["x"], part["y"]):
            raise ValueError(f"Safari : habitat mal rattaché : {part['const']}")
        left, top, right, bottom = row["x"], row["y"], row["x"] + row["width"], row["y"] + row["height"]
        if not 0 <= left < right <= atlas["width"] or not 0 <= top < bottom <= atlas["height"]:
            raise ValueError(f"Safari : habitat hors atlas : {part['const']}")
        if any(left < x2 and right > x1 and top < y2 and bottom > y1 for x1, y1, x2, y2 in rectangles):
            raise ValueError(f"Safari : habitats superposés : {part['const']}")
        rectangles.append((left, top, right, bottom))
