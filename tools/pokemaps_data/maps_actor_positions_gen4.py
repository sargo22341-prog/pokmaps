"""Dégagement des marqueurs DS placés sur une entrée, sur les cases libres du même lieu."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps_actor_positions import clears_passages
from .pret_gen4_map_models import EMPTY_BLOCK

if TYPE_CHECKING:
    from .maps import GameMapData
    from .maps_characters import ObjectRow
    from .maps_export_gen4 import Gen4MapProjection


def clear_actor_passages(data: GameMapData, projection: Gen4MapProjection) -> None:
    regions = {row.const: row for row in data.maps}
    for obj in data.objects:
        passages = {(w.x, w.y) for w in data.warps if w.map_const == obj.map_const}
        if obj.kind not in {"npc", "trainer", "npc_pokemon"} or (obj.x, obj.y) not in passages:
            continue
        region = regions[obj.map_const]
        occupied = {(other.x, other.y) for other in data.objects if other.map_const == obj.map_const}
        candidates = [
            point
            for point in _points(obj, projection)
            if region.x <= point[0] <= region.x + region.width
            and region.y <= point[1] <= region.y + region.height
            and point not in occupied
            and clears_passages(point, passages)
        ]
        if not candidates:
            raise ValueError(f"{obj.map_const}:{obj.key} : aucune case libre à distance du passage")
        obj.x, obj.y = min(candidates, key=lambda p: ((p[0] - obj.x) ** 2 + (p[1] - obj.y) ** 2, p))


def _points(obj: ObjectRow, projection: Gen4MapProjection) -> list[tuple[int, int]]:
    maps = projection.maps
    header = maps.headers[obj.map_const]
    matrix = maps.repo.matrices[header.matrix]
    surfable = maps.context.rules.tiles.surfable
    offset_x, _, offset_z = projection.offsets.get(header.index, (0, 0, 0))
    if obj.source_cell:
        start_x, start_z = obj.source_cell
    else:
        # Un combat de scène sans événement posé est représenté sur une case libre de son lieu.
        display = maps.displays[maps.parents[obj.map_const]]
        start_x = (obj.x + display.bounds[0]) // 16 + offset_x
        start_z = (obj.y + display.bounds[1]) // 16 + offset_z
    cells = [(start_x + dx, start_z + dz) for dz in range(-8, 9) for dx in range(-8, 9)]
    result = []
    for x, z in cells:
        local_x, local_z = x - offset_x, z - offset_z
        if not (0 <= local_x < matrix.width * 32 and 0 <= local_z < matrix.height * 32):
            continue
        number = matrix.blocks[local_z // 32][local_x // 32]
        if number == EMPTY_BLOCK:
            continue
        if matrix.headers is not None and matrix.headers[local_z // 32][local_x // 32] != header.index:
            continue
        block = maps.repo.land_block(number)
        if block.collision(local_x % 32, local_z % 32):
            continue
        if block.behavior(local_x % 32, local_z % 32) in surfable:
            continue
        result.append(projection.point(obj.map_const, x, z))
    return result
