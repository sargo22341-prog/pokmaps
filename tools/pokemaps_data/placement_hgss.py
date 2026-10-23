"""Couverture des rencontres HGSS sur les terrains de l'atlas, indépendante d'Android."""

import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from PIL import Image

from .grass_placement_hgss import align_grass
from .map_spots import TerrainKey, read_spots, selected_key
from .maps_layout import identifier
from .maps_render_hgss import HgssRenderer
from .pret_hgss_maps import HgssMapRepo
from .terrain_hgss import projected_cells, tile_flags
from .visibility_hgss import visible_surfaces
from .water_placement_hgss import read_water_regions, water_points
from .world_placement_hgss import visible_world_cells

FAMILY = "heartgold-soulsilver"


def read_placement_json(path: Path) -> dict:
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError(f"{path} : catalogue de placement trop volumineux")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} : objet JSON attendu")
    return data


def spread_pixels(points: list[tuple[int, int]], seed: str) -> list[tuple[int, int]]:
    order = sorted(points)
    random.Random(seed).shuffle(order)
    chosen = []
    for point in order:
        if len(chosen) >= 40:
            break
        if all((point[0] - x) ** 2 + (point[1] - y) ** 2 >= 32**2 for x, y in chosen):
            chosen.append(point)
    return sorted(chosen)


def points_digest(points: frozenset[tuple[int, int]]) -> str:
    return hashlib.sha256(json.dumps(sorted(points), separators=(",", ":")).encode("ascii")).hexdigest()


def encounter_lines(catalog: dict) -> dict[int, dict[tuple[str, str, int], tuple[int, int]]]:
    banks = {b["bank"]: b["headers"] for b in catalog["banks"]}
    found: dict[int, dict] = defaultdict(dict)
    for table in catalog["distributions"] + catalog["headbutt"]:
        headers = [table["bank"]] if table["method"].startswith("headbutt-") else banks[table["bank"]]
        method = "headbutt" if table["method"].startswith("headbutt-") else table["method"]
        for header in headers:
            for slot in table["slots"]:
                _add_line(found[header], table["version"], method, slot)
    for table in catalog["special_wild"]["contest"]:
        for version in catalog["versions"]:
            for slot in table["slots"]:
                _add_line(found[487], version, "walk", slot)
    _safari_lines(catalog, found)
    return dict(found)


def _add_line(found: dict, version: str, method: str, slot: dict) -> None:
    key = version, method, slot["species"]
    old = found.get(key, (slot["minimum"], slot["maximum"]))
    found[key] = min(old[0], slot["minimum"]), max(old[1], slot["maximum"])


def _safari_lines(catalog: dict, found: dict) -> None:
    special = catalog["special_wild"]
    for area, table in enumerate(special["safari"]):
        for native, method in zip(
            ("land", "surf", "oldrod", "goodrod", "superrod"),
            ("walk", "surf", "old-rod", "good-rod", "super-rod"),
            strict=True,
        ):
            for period in ("morn", "day", "nite"):
                mons = table[native]["mons"][period] + [b[period] for b in table[native]["bonus_mons"]]
                for mon in mons:
                    slot = dict(
                        species=special["species_ids"][mon["species"]], minimum=mon["level"], maximum=mon["level"]
                    )
                    for version in catalog["versions"]:
                        _add_line(found[343 + area], version, method, slot)


def placement_catalog(root: Path, maps: Path, encounters: dict) -> dict:
    repo = HgssMapRepo(root, "heartgold")
    atlas = read_placement_json(maps / "atlas/catalog.json")
    records = {r["header"]: r for r in atlas["maps"]}
    plans = {p["id"]: p for p in atlas["plans"]}
    offsets = {p["header"]: p["offset"] for plan in atlas["plans"] for p in plan["parts"]}
    warps: dict[int, list] = defaultdict(list)
    for passage in atlas["passages"]:
        offset = offsets[passage["source"]]
        warps[passage["source"]].append([passage["source_pixel"][i] - offset[i] for i in (0, 1)])
    flags = tile_flags(root)
    water_regions = read_water_regions()
    renderer = HgssRenderer(repo)
    trees = {
        row["header"]: {(p["x"], p["y"]) for group in row["regular"] + row["secret"] for p in group}
        for row in encounters["headbutt_context"]["trees"]
    }
    result = []
    exclusions = {r["header"]: r["reason"] for r in atlas["inventory"] if r["scope"] == "excluded"}
    excluded = []
    for header, lines in sorted(encounter_lines(encounters).items()):
        if header not in records:
            if not exclusions.get(header):
                raise ValueError(f"HGSS : rencontres sans carte ni exclusion : {header}")
            excluded.append(dict(header=header, reason=exclusions[header]))
            continue
        record = records[header]
        methods = {method for _, method, _ in lines}
        cells, rejected, depths = projected_cells(repo, record, methods, trees.get(header, set()), flags)
        cells = visible_cells(maps / "atlas" / record["image"], cells, rejected)
        # Les plans d'eau visuels ne suivent pas toujours le BDHC ; leur curation se relit sur les images.
        water = cells.pop("water", [])
        if header in water_regions:
            water = water_points(maps / "atlas" / record["image"], water_regions[header])
        cells = visible_surfaces(renderer, record, cells, depths, rejected)
        if water:
            cells["water"] = water
        cells = align_grass(maps / "atlas" / record["image"], cells, record["const"])
        cells = visible_world_cells(maps / "atlas", record, cells, plans[record["plan"]], offsets[header], rejected)
        result.append(
            record
            | dict(
                identifier=identifier(record["const"]),
                terrain=cells,
                rejected=rejected,
                lines=[
                    dict(version=v, method=m, species=s, minimum=levels[0], maximum=levels[1])
                    for (v, m, s), levels in sorted(lines.items())
                ],
                generated={kind: spread_pixels(points, f"{header}/{kind}") for kind, points in cells.items()},
                warps=warps[header],
            )
        )
    if unknown := water_regions.keys() - {r["header"] for r in result}:
        raise ValueError(f"HGSS : surfaces aquatiques sans rencontre native : {sorted(unknown)}")
    return dict(maps=result, excluded=excluded, species_fr=encounters["species_fr"])


def visible_cells(path: Path, cells: dict, rejected: list[dict]) -> dict:
    result = {}
    with Image.open(path) as image:
        pixels = image.convert("RGBA")
        for kind, points in cells.items():
            accepted = []
            for point in points:
                red, green, blue, alpha = pixels.getpixel(point)
                # Certains plans techniques rendent aussi un rectangle noir opaque hors du décor visible.
                water = kind != "water" or (blue - red >= 24 and blue >= green)
                if alpha and max(red, green, blue) > 8 and water:
                    accepted.append(point)
                else:
                    rejected.append(
                        dict(point=point, kind=kind, reason="projection hors décor visible ou hors eau visible")
                    )
            if accepted:
                result[kind] = accepted
    return result


def coverage(catalog: dict, path: Path) -> list[dict]:
    spots = read_spots(path)
    rows = []
    known = set()
    for record in catalog["maps"]:
        methods = {line["method"] for line in record["lines"]}
        kinds = set(record["terrain"])
        if "walk" in methods:
            kinds.add("grass" if record["terrain"].get("grass") else "floor")
        if methods & {"surf", "old-rod", "good-rod", "super-rod"}:
            kinds.add("water")
        kinds.update(kind for method, kind in (("headbutt", "tree"), ("rock-smash", "rock")) if method in methods)
        for kind in sorted(kinds):
            key = TerrainKey(FAMILY, record["identifier"], kind)
            known.add(key)
            selected = selected_key(spots, key, FAMILY)
            points = spots.get(selected, frozenset())
            valid = {tuple(p) for p in record["terrain"].get(kind, [])}
            if invalid := points - valid:
                raise ValueError(f"HGSS {key} : points hors terrain : {sorted(invalid)}")
            rows.append(
                dict(
                    header=record["header"],
                    map=key.map_identifier,
                    scope=record["scope"],
                    kind=kind,
                    points=len(points),
                    points_sha256=points_digest(points),
                    available=len(valid),
                )
            )
    unknown = [
        key
        for key in spots
        if key.family == FAMILY and TerrainKey(key.family, key.map_identifier, key.kind) not in known
    ]
    if unknown:
        raise ValueError(f"HGSS : retouches sans terrain attendu : {unknown}")
    return rows
