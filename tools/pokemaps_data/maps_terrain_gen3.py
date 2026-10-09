"""Cases sauvages du moteur GBA, limitées aux méthodes présentes sur la carte."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .map_spots import SPOT_KINDS
from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo
    from .pret_gen3_maps import Gen3Map


@dataclass(frozen=True)
class TerrainRules:
    land: frozenset[int]
    water: frozenset[int]
    surfable: frozenset[int]


def terrain_rules(repo: Gen3PretRepo) -> TerrainRules:
    header = read_text(repo.root / "include/constants/metatile_behaviors.h")
    defines = re.findall(r"#define\s+(MB_\w+)\s+(0x[0-9A-Fa-f]+|\d+)", header)
    constants = {name: int(value, 0) for name, value in defines}
    if not constants:
        constants = {name: index for index, name in enumerate(re.findall(r"^\s*(MB_\w+),", header, re.M))}
    text = read_text(repo.root / "src/metatile_behavior.c")
    if repo.remake:
        body = _table(text, "sBehaviorSurfable")
        water = frozenset(constants[name] for name in re.findall(r"\[(MB_\w+)\]\s*=\s*TRUE", body))
        return TerrainRules(frozenset(), frozenset(), water)
    body = _table(text, "sTileBitAttributes")
    if repo.ruby:
        flags = re.findall(r"TILE_ATTRIBUTES\((TRUE|FALSE),\s*(TRUE|FALSE),\s*(TRUE|FALSE)\)", body)
        if not flags or len(flags) > 256:
            raise ValueError(f"{repo.root} : attributs de terrain invalides")
        water = frozenset(index for index, (_, surf, _) in enumerate(flags) if surf == "TRUE")
        encounter = frozenset(index for index, (_, _, wild) in enumerate(flags) if wild == "TRUE")
    else:
        entries = re.findall(r"\[(MB_\w+)\]\s*=\s*([^,]+),", body)
        water = frozenset(constants[name] for name, value in entries if "TILE_FLAG_SURFABLE" in value)
        encounter = frozenset(constants[name] for name, value in entries if "TILE_FLAG_HAS_ENCOUNTERS" in value)
    if not encounter or not water:
        raise ValueError(f"{repo.root} : règles sauvages vides")
    return TerrainRules(encounter - water, encounter & water, water)


def _table(text: str, name: str) -> str:
    match = re.search(re.escape(name) + r"\[[^;]+?=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise ValueError(f"Table de terrain absente : {name}")
    return match[1]


def wild_cells(repo: Gen3PretRepo, current: Gen3Map) -> dict[str, list[tuple[int, int]]]:
    result: dict[str, list[tuple[int, int]]] = {kind: [] for kind in SPOT_KINDS}
    methods = repo.wild_methods.get(current.const, frozenset())
    if not methods:
        return result
    rules = repo.terrain_rules
    warps = {(warp.x, warp.y) for warp in current.warps}
    primary = repo.tilesets[current.layout.primary_tileset]
    secondary = repo.tilesets[current.layout.secondary_tileset]
    for y in range(current.height):
        for x in range(current.width):
            if (x, y) in warps or (current.layout.cells[y * current.width + x] >> 10) & 3:
                continue
            number = current.block(x, y)
            source = primary if number < primary.primary_metatile_count else secondary
            index = number if source is primary else number - primary.primary_metatile_count
            tile = source.metatiles[index]
            land = tile.encounter_type == 1 if repo.remake else tile.behavior in rules.land
            water = tile.encounter_type == 2 if repo.remake else tile.behavior in rules.water
            if "walk" in methods and land:
                grass = (2, 0xD1) if repo.remake else (2, 3, 0x24)
                kind = "grass" if tile.behavior in grass else "floor"
                result[kind].append((x, y))
            fishing = bool(methods & {"old-rod", "good-rod", "super-rod"})
            if water and "seaweed" in methods:
                result["underwater"].append((x, y))
            if (water and "surf" in methods) or (fishing and tile.behavior in rules.surfable):
                result["water"].append((x, y))
    if "rock-smash" in methods:
        result["rock"] = [
            (obj.x, obj.y)
            for obj in current.objects
            if obj.value("graphics_id") in {"OBJ_EVENT_GFX_ROCK_SMASH_ROCK", "OBJ_EVENT_GFX_BREAKABLE_ROCK"}
            and obj.value("script") in {"EventScript_RockSmash", "S_BreakableRock"}
        ]
    return result
