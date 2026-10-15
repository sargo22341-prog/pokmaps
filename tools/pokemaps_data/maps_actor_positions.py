"""Placement affiché des personnages à côté des passages, sans modifier les événements source."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import replace

from .maps_characters import ObjectRow
from .maps_layout import GameMaps
from .maps_terrain_gen3 import behavior_constants
from .pret import PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_gen3 import Gen3PretRepo


def clear_actor_passages(maps: GameMaps, rows: list[ObjectRow]) -> list[ObjectRow]:
    grouped: dict[str, list[tuple[int, ObjectRow]]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[row.map_const].append((index, row))
    result = list(rows)
    for const, indexed in grouped.items():
        actors = [row for _, row in indexed]
        current = maps.maps[const]
        warps = {maps.point(const, warp.x, warp.y) for warp in current.warps}
        occupied = {(row.x, row.y) for row in actors}
        moved: dict[tuple[int, int, str | None], tuple[int, int]] = {}
        for index, row in indexed:
            if row.kind not in {"npc", "trainer", "npc_pokemon"} or (row.x, row.y) not in warps:
                continue
            key = (row.x, row.y, row.key)
            if key not in moved:
                moved[key] = _nearby_position(maps, const, row, warps | occupied)
                occupied.add(moved[key])
            result[index] = replace(row, x=moved[key][0], y=moved[key][1])
    return result


def _nearby_position(maps: GameMaps, const: str, row: ObjectRow, blocked: set[tuple[int, int]]) -> tuple[int, int]:
    warps = _passage_points(maps, const)
    candidates = [
        point
        for point in _reachable_positions(maps, const, row, warps)
        if point not in blocked and clears_passages(point, warps)
    ]
    if not candidates:
        raise ValueError(f"{maps.game.version_group}:{const}:{row.key} : aucune case libre à distance des passages")
    # À distance égale, dégager l'axe de la porte plutôt que se poster directement devant.
    return min(candidates, key=lambda p: ((p[0] - row.x) ** 2 + (p[1] - row.y) ** 2, p[0] == row.x, -p[1], p[0]))


def clears_passages(point: tuple[int, int], warps: set[tuple[int, int]]) -> bool:
    # Sprite de 16 × 32 px, pieds en bas de case : garder 16 px vides entre son cadre et le passage.
    return all(abs(point[0] - x) >= 32 or point[1] - y >= 48 or y - point[1] >= 32 for x, y in warps)


def _reachable_positions(
    maps: GameMaps, const: str, row: ObjectRow, warps: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    start = (row.x, row.y)
    pending = deque([start])
    seen = {start}
    reachable = []
    origin = maps.point(const, 0, 0)
    while pending:
        point = pending.popleft()
        for dx, dy in ((0, 16), (-16, 0), (16, 0), (0, -16)):
            neighbor = (point[0] + dx, point[1] + dy)
            if neighbor in seen or abs(neighbor[0] - row.x) + abs(neighbor[1] - row.y) > 128:
                continue
            seen.add(neighbor)
            # La moitié haute de certaines portes extérieures appartient visuellement à la façade.
            if (
                isinstance(maps.repo, Gen3PretRepo)
                and maps.maps[const].is_outdoor
                and (neighbor[0], neighbor[1] + 16) in warps
            ):
                continue
            x, y = (neighbor[0] - origin[0]) // 16, (neighbor[1] - origin[1]) // 16
            if not _walkable(maps, const, x, y):
                continue
            reachable.append(neighbor)
            pending.append(neighbor)
    return reachable


def _passage_points(maps: GameMaps, const: str) -> set[tuple[int, int]]:
    current = maps.maps[const]
    if not isinstance(maps.repo, Gen3PretRepo) or not current.label.startswith("LavaridgeTown_Gym"):
        return {maps.point(const, warp.x, warp.y) for warp in current.warps}
    # Les dresseurs surgissent des trappes ; seules les véritables portes demandent une zone de dégagement.
    constants = behavior_constants(maps.repo)
    traps = {value for name, value in constants.items() if name.startswith("MB_LAVARIDGE_") and "WARP" in name}
    return {
        maps.point(const, warp.x, warp.y)
        for warp in current.warps
        if maps._behavior(current, warp.x, warp.y) not in traps
    }


def _walkable(maps: GameMaps, const: str, x: int, y: int) -> bool:
    current, repo = maps.maps[const], maps.repo
    factor = 1 if isinstance(repo, Gen3PretRepo) else 2
    if not (0 <= x < current.width * factor and 0 <= y < current.height * factor):
        return False
    match repo:
        case Gen3PretRepo():
            return ((current.layout.cells[y * current.width + x] >> 10) & 3) == 0
        case Gen2PretRepo():
            tileset = repo.tilesets[current.tileset]
            collision = tileset.collisions[current.block(x // 2, y // 2)][(y % 2) * 2 + x % 2]
            return repo.collisions.permissions[collision] == "LAND_TILE"
        case PretRepo():
            tile = repo.tile_at(current, x * 2, y * 2 + 1)
            return tile in repo.tilesets[current.tileset].passable
