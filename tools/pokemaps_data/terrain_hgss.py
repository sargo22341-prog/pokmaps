"""Cases HGSS et projection dans le repère natif des images de l'atlas."""

import re
from dataclasses import dataclass
from pathlib import Path

from .maps_render_hgss import camera_cotangent
from .pret_gen4_land import FX_ONE, LandBlock, heights
from .pret_gen4_source import read_text
from .pret_hgss_maps import HgssMapRepo

Cell = tuple[int, int]


@dataclass(frozen=True)
class ProjectedSurface:
    point: Cell
    depth: int


def tile_flags(root: Path) -> dict[int, str]:
    constants = read_text(root / "include/constants/metatile_behavior.h")
    body = constants.split("enum", 1)[1].split("{", 1)[1].split("}", 1)[0]
    names = re.findall(r"\bTILE_BEHAVIOR_\w+\b", body)
    source = read_text(root / "src/metatile_behavior.c")
    pairs = re.findall(r"\[(TILE_BEHAVIOR_\w+)\]\s*=\s*TILE_BEHAVIOR_FLAG_(\w+)", source)
    if len(names) != 238 or len(pairs) != 237 or {n for n, _ in pairs} != set(names) - {"TILE_BEHAVIOR_NONE"}:
        raise ValueError("HGSS : table des comportements de terrain inattendue")
    return {names.index(name): flag for name, flag in pairs}


def terrain_kind(behavior: int, collision: bool, flags: dict[int, str], methods: set[str]) -> str | None:
    flag = flags[behavior]
    if "SURFABLE" in flag:
        fishing = bool(methods & {"old-rod", "good-rod", "super-rod"})
        return "water" if fishing or ("surf" in methods and "ENCOUNTER" in flag) else None
    if "walk" in methods and "ENCOUNTER" in flag and not collision:
        return "grass" if behavior in (2, 3) else "floor"
    return None


def projected_cells(
    repo: HgssMapRepo, record: dict, methods: set[str], trees: set[Cell], flags: dict[int, str]
) -> tuple[dict[str, list[Cell]], list[dict], dict[Cell, int]]:
    header = repo.headers[record["header"]]
    events = repo.events(header)
    occupied = {(w.x, w.z) for w in events.warps} | {(a.x, a.z) for a in events.actors}
    rocks = {(a.x, a.z) for a in events.actors if a.sprite == "SPRITE_BREAKROCK"}
    cotangent = camera_cotangent(repo.root, header)
    result: dict[str, list[Cell]] = {}
    rejected = []
    depths = {}
    for column, row, number, altitude in repo.blocks(header):
        block = repo.land(number)
        for z in range(32):
            for x in range(32):
                cell = column * 32 + x, row * 32 + z
                kind = terrain_kind(block.behavior(x, z), block.collision(x, z), flags, methods)
                if cell in occupied:
                    kind = None
                if cell in trees:
                    kind = "tree"
                if cell in rocks and "rock-smash" in methods:
                    kind = "rock"
                if kind is None:
                    continue
                surface, reason = project_cell(block, cell, altitude, cotangent, record, allow_levels=kind == "water")
                if surface is None:
                    rejected.append(dict(cell=cell, kind=kind, reason=reason))
                else:
                    result.setdefault(kind, []).append(surface.point)
                    depths[surface.point] = surface.depth
    return {kind: sorted(set(points)) for kind, points in result.items()}, rejected, depths


def project_cell(
    block: LandBlock, cell: Cell, altitude: int, cotangent: int, record: dict, *, allow_levels: bool = False
) -> tuple[ProjectedSurface | None, str]:
    values = (
        ()
        if block.bdhc is None
        else heights(block.bdhc, (cell[0] % 32 * 16 - 248) * FX_ONE, (cell[1] % 32 * 16 - 248) * FX_ONE)
    )
    if not values:
        return None, "sans surface BDHC"
    if not allow_levels and values[-1] - values[0] >= 16 * FX_ONE:
        return None, "surfaces superposées : aucun point sur le plan supérieur"
    height = values[-1] + altitude * 8 * FX_ONE
    origin = record["origin_pixels"]
    point = cell[0] * 16 + 8 - origin[0], cell[1] * 16 + 8 - height * cotangent // FX_ONE // FX_ONE - origin[1]
    if not (0 <= point[0] < record["size"][0] and 0 <= point[1] < record["size"][1]):
        return None, "projection hors image"
    depth = height + (cell[1] * 16 + 8) * cotangent
    return ProjectedSurface(point, depth), ""
