"""Dégagement des entrées et espacement des partenaires sur les cartes DS."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from .maps_actor_positions import clears_passages
from .pret_gen4_map_models import EMPTY_BLOCK
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .maps import GameMapData
    from .maps_characters import ObjectRow
    from .maps_export_gen4 import Gen4MapProjection

_DUO_CLASSES = frozenset({"twins", "young_couple", "double_team", "sis_and_bro", "interviewers"})


def curated_positions(data: GameMapData, projection: Gen4MapProjection) -> None:
    family = projection.maps.game.version_group
    actors = {obj.key: obj for obj in data.objects if obj.key}
    seen = set()
    with (DATA_DIR / "map_actor_positions_gen4.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["family"] != family:
                continue
            key = row["key"]
            if key in seen or key not in actors or not row["reason"].strip():
                raise ValueError(f"map_actor_positions_gen4.csv : personnage inconnu, répété ou sans raison : {key}")
            seen.add(key)
            obj = actors[key]
            cell = (int(row["x"]), int(row["z"]))
            point = projection.point(obj.map_const, *cell)
            if point not in _points(obj, projection):
                raise ValueError(f"map_actor_positions_gen4.csv : case non praticable : {key}:{cell}")
            obj.x, obj.y = point
            obj.source_cell = cell


def space_trainer_duos(objects: list[ObjectRow]) -> None:
    """Écarte les partenaires en gardant leur centre, leur alignement et leur case source."""
    pending = [
        obj for obj in objects if obj.kind == "trainer" and obj.sprite is not None and obj.trainer_class in _DUO_CLASSES
    ]
    paired: set[int] = set()
    for index, actor in enumerate(pending):
        if index in paired:
            continue
        partners = [
            (other_index, other)
            for other_index, other in enumerate(pending)
            if other_index != index
            and other_index not in paired
            and (actor.map_const, actor.trainer_class, actor.name_fr)
            == (other.map_const, other.trainer_class, other.name_fr)
            and (actor.x == other.x or actor.y == other.y)
            and abs(actor.x - other.x) + abs(actor.y - other.y) == 16
        ]
        if len(partners) != 1:
            continue
        other_index, other = partners[0]
        if actor.y == other.y:
            left, right = sorted((actor, other), key=lambda obj: obj.x)
            left.x -= 4
            right.x += 4
        else:
            top, bottom = sorted((actor, other), key=lambda obj: obj.y)
            top.y -= 8
            bottom.y += 8
        paired.update((index, other_index))


def clear_actor_passages(data: GameMapData, projection: Gen4MapProjection) -> None:
    regions = {row.const: row for row in data.maps}
    for obj in data.objects:
        passages = {(w.x, w.y) for w in data.warps if w.map_const == obj.map_const}
        outdoor = projection.maps.repo.matrices[projection.maps.headers[obj.map_const].matrix].headers is not None
        blocked = not clears_passages((obj.x, obj.y), passages) if outdoor else (obj.x, obj.y) in passages
        if obj.kind not in {"npc", "trainer", "npc_pokemon"} or not blocked:
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


def space_characters(data: GameMapData, projection: Gen4MapProjection, source: Path) -> None:
    """Dégage aussi les personnages de scénario et les petits objets comme la mallette."""
    placed: dict[str, list[tuple[int, int, int, int]]] = {}
    frames = _sprite_frames(data.objects, source)
    for obj in data.objects:
        if obj.sprite is None or obj.kind == "pokemon":
            continue
        parent = projection.maps.parents[obj.map_const]
        occupied = placed.setdefault(parent, [])
        point = (obj.x, obj.y)
        frame = frames[obj.sprite]
        walkable = _points(obj, projection) if obj.trainer_class in _DUO_CLASSES else None
        if not _clears_frame(point, frame, occupied) or (walkable is not None and point not in walkable):
            passages = {(w.x, w.y) for w in data.warps if projection.maps.parents[w.map_const] == parent}
            available = walkable if walkable is not None else _points(obj, projection)
            candidates = [p for p in available if _clears_frame(p, frame, occupied) and clears_passages(p, passages)]
            if not candidates:
                raise ValueError(f"{obj.map_const}:{obj.key} : aucune case libre pour espacer le personnage")
            point = min(candidates, key=lambda p: ((p[0] - obj.x) ** 2 + (p[1] - obj.y) ** 2, p))
            obj.x, obj.y = point
        occupied.append((point[0] + frame[0], point[1] + frame[1], point[0] + frame[2], point[1] + frame[3]))


def _sprite_frames(objects: list[ObjectRow], source: Path) -> dict[str, tuple[int, int, int, int]]:
    frames = {}
    for sprite in sorted({obj.sprite for obj in objects if obj.sprite is not None}):
        with Image.open(source / "sprites" / f"{sprite}.webp") as image:
            box = image.convert("RGBA").getbbox()
            if box is None:
                raise ValueError(f"Sprite DS vide : {sprite}")
            dx, dy = -image.width // 2, 8 - image.height
            frames[sprite] = (dx + box[0], dy + box[1], dx + box[2], dy + box[3])
    return frames


def _clears_frame(
    point: tuple[int, int],
    frame: tuple[int, int, int, int],
    occupied: list[tuple[int, int, int, int]],
) -> bool:
    left, top, right, bottom = (point[0] + frame[0], point[1] + frame[1], point[0] + frame[2], point[1] + frame[3])
    return all(right + 4 <= x1 or x2 + 4 <= left or bottom + 4 <= y1 or y2 + 4 <= top for x1, y1, x2, y2 in occupied)


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
