"""Cartes GBA : layouts de 16 px et événements, sans interprétation des scripts."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pret_gen3_source import read_json, read_text, source_path
from .pret_gen3_validation import validate_layout, validate_map
from .pret_models import Connection

MAX_MAPS = 1024
MAX_MAP_CELLS = 1024 * 1024


@dataclass(frozen=True)
class Gen3Event:
    kind: str
    x: int
    y: int
    elevation: int
    fields: tuple[tuple[str, str | int | bool], ...]

    def value(self, name: str) -> str | int | bool:
        return dict(self.fields)[name]


@dataclass(frozen=True)
class Gen3Warp:
    x: int
    y: int
    target: str
    # Numérotation commune, à partir de 1 ; 0 = aucun, 127 = Base Secrète, 128 = destination dynamique.
    target_warp: int
    elevation: int
    accessible: bool = True


@dataclass(frozen=True)
class Gen3Layout:
    const: str
    width: int
    height: int
    primary_tileset: str
    secondary_tileset: str
    cells: tuple[int, ...]
    border_width: int
    border_height: int
    border: tuple[int, ...]

    def block(self, x: int, y: int) -> int:
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ValueError(f"{self.const} : case hors du layout : {x}, {y}")
        return self.cells[y * self.width + x] & 0x3FF


@dataclass(frozen=True)
class Gen3Map:
    const: str
    label: str
    number: int
    group: int
    group_index: int
    layout: Gen3Layout
    map_type: str
    region_map_section: str
    connections: tuple[Connection, ...]
    warps: tuple[Gen3Warp, ...]
    objects: tuple[Gen3Event, ...]
    coord_events: tuple[Gen3Event, ...]
    bg_events: tuple[Gen3Event, ...]
    shared_events_map: str | None
    shared_scripts_map: str | None
    settings: tuple[tuple[str, str | int | bool], ...]

    @property
    def width(self) -> int:
        return self.layout.width

    @property
    def height(self) -> int:
        return self.layout.height

    def block(self, x: int, y: int) -> int:
        return self.layout.block(x, y)

    @property
    def is_outdoor(self) -> bool:
        return self.map_type in {
            "MAP_TYPE_TOWN",
            "MAP_TYPE_CITY",
            "MAP_TYPE_ROUTE",
            "MAP_TYPE_OCEAN_ROUTE",
            "MAP_TYPE_6",
        }


def _words(path: Path, count: int) -> tuple[int, ...]:
    if path.stat().st_size != count * 2:
        raise ValueError(f"{path} : {count * 2} octets attendus")
    return struct.unpack(f"<{count}H", path.read_bytes())


def read_layouts(root: Path) -> dict[str, Gen3Layout]:
    rows = read_json(root / "data/layouts/layouts.json")["layouts"]
    if not isinstance(rows, list) or not 0 < len(rows) <= MAX_MAPS:
        raise ValueError(f"{root} : nombre de layouts invalide")
    labels = read_groups(root)
    used = {read_json(source_path(root, f"data/maps/{label}/map.json"))["layout"] for _, _, label in labels}
    used.update(_mirage_layouts(root, rows))
    result: dict[str, Gen3Layout] = {}
    for row in rows:
        if row == {}:
            continue
        validate_layout(row, str(root))
        # Les layouts non référencés incluent des prototypes tronqués ; ils ne décrivent aucune carte du jeu.
        if row["id"] not in used:
            continue
        width, height = row["width"], row["height"]
        bw, bh = row.get("border_width", 2), row.get("border_height", 2)
        if any(type(size) is not int or not 0 < size <= 1024 for size in (width, height, bw, bh)):
            raise ValueError(f"{root} : dimensions invalides pour {row['id']}")
        if width * height > MAX_MAP_CELLS or row["id"] in result:
            raise ValueError(f"{root} : layout invalide ou répété : {row['id']}")
        result[row["id"]] = Gen3Layout(
            row["id"],
            width,
            height,
            row["primary_tileset"],
            row["secondary_tileset"],
            _words(source_path(root, row["blockdata_filepath"]), width * height),
            bw,
            bh,
            _words(source_path(root, row["border_filepath"]), bw * bh),
        )
    return result


def _mirage_layouts(root: Path, rows: list[dict[str, Any]]) -> set[str]:
    script = root / "data/maps/Route130/scripts.inc"
    if not script.is_file():
        return set()
    references = re.findall(r"^\s*setmaplayoutindex\s+(\w+)", read_text(script), re.M)
    if len(set(references)) != 2:
        raise ValueError(f"{script} : deux layouts attendus pour l’Île Mirage")
    result = set()
    for reference in references:
        if reference.isdecimal():
            index = int(reference) - 1
            if not 0 <= index < len(rows) or not rows[index]:
                raise ValueError(f"{script} : layout absent : {reference}")
            reference = rows[index]["id"]
        result.add(reference)
    return result


def _events(rows: list[dict[str, Any]], category: str) -> tuple[Gen3Event, ...]:
    result = []
    for row in rows:
        kind = row.get("type", "object" if category == "object" else "")
        if kind == "clone":
            continue
        result.append(Gen3Event(kind, row["x"], row["y"], row["elevation"], tuple(row.items())))
    return tuple(result)


def _connections(row: dict[str, Any]) -> tuple[Connection, ...]:
    directions = {"up": "north", "down": "south", "left": "west", "right": "east", "dive": "dive", "emerge": "emerge"}
    result = []
    for connection in row.get("connections") or []:
        if connection["direction"] not in directions or type(connection["offset"]) is not int:
            raise ValueError(f"{row['id']} : connexion invalide : {connection}")
        result.append(Connection(directions[connection["direction"]], connection["map"], connection["offset"]))
    return tuple(result)


def _warps(row: dict[str, Any]) -> tuple[Gen3Warp, ...]:
    result = []
    for warp in row.get("warp_events", []):
        destination = str(warp["dest_warp_id"])
        if destination in {"WARP_ID_DYNAMIC", "WARP_ID_SECRET_BASE", "WARP_ID_NONE"}:
            number = {"WARP_ID_DYNAMIC": 128, "WARP_ID_SECRET_BASE": 127, "WARP_ID_NONE": 0}[destination]
        else:
            try:
                number = int(destination, 0) + 1
            except ValueError as error:
                raise ValueError(f"{row['id']} : warp inconnu : {destination}") from error
        if not 0 <= number <= 256:
            raise ValueError(f"{row['id']} : numéro de warp invalide : {destination}")
        result.append(Gen3Warp(warp["x"], warp["y"], warp["dest_map"], number, warp["elevation"]))
    return tuple(result)


def read_maps(root: Path, layouts: dict[str, Gen3Layout]) -> dict[str, Gen3Map]:
    labels = read_groups(root)
    rows = {label: read_json(source_path(root, f"data/maps/{label}/map.json")) for _, _, label in labels}
    for label, row in rows.items():
        validate_map(row, label)
    result: dict[str, Gen3Map] = {}
    for group, index, label in labels:
        row = rows[label]
        events = row
        shared = row.get("shared_events_map")
        if shared:
            if shared not in rows or rows[shared].get("shared_events_map"):
                raise ValueError(f"{label} : événements partagés absents ou chaînés : {shared}")
            events = rows[shared]
        if row["id"] in result or row["layout"] not in layouts:
            raise ValueError(f"{label} : carte répétée ou layout absent")
        result[row["id"]] = Gen3Map(
            row["id"],
            label,
            len(result) + 1,
            group,
            index,
            layouts[row["layout"]],
            row["map_type"],
            row["region_map_section"],
            _connections(row),
            _warps(events),
            _events(events.get("object_events", []), "object"),
            _events(events.get("coord_events", []), "coord"),
            _events(events.get("bg_events", []), "bg"),
            shared,
            row.get("shared_scripts_map"),
            tuple(
                (key, value)
                for key, value in row.items()
                if key not in {"connections", "object_events", "warp_events", "coord_events", "bg_events"}
            ),
        )
    _validate_targets(result)
    return result


def _validate_targets(maps: dict[str, Gen3Map]) -> None:
    special = {"MAP_DYNAMIC", "MAP_UNDEFINED", "MAP_NONE"}
    for map_data in maps.values():
        for connection in map_data.connections:
            if connection.target not in maps:
                raise ValueError(f"{map_data.const} : connexion vers {connection.target} absente")
        for warp in map_data.warps:
            if warp.target not in maps and warp.target not in special:
                raise ValueError(f"{map_data.const} : warp vers {warp.target} absent")
            if warp.target in maps and 0 < warp.target_warp < 127 and warp.target_warp > len(maps[warp.target].warps):
                raise ValueError(f"{map_data.const} : warp d’arrivée absent : {warp.target} #{warp.target_warp}")


def read_groups(root: Path) -> list[tuple[int, int, str]]:
    path = root / "data/maps/map_groups.json"
    groups = read_json(path)
    order = groups.get("group_order")
    if not isinstance(order, list) or not 0 < len(order) <= 256 or any(not isinstance(name, str) for name in order):
        raise ValueError(f"{path} : ordre des groupes invalide")
    if len(set(order)) != len(order) or groups.keys() - {*order, "group_order", "connections_include_order"}:
        raise ValueError(f"{path} : groupes répétés ou inconnus")
    labels = []
    for group, name in enumerate(order):
        maps = groups.get(name)
        if not isinstance(maps, list) or len(maps) > 256 or any(not isinstance(label, str) for label in maps):
            raise ValueError(f"{path} : groupe invalide : {name}")
        labels.extend((group, index, label) for index, label in enumerate(maps))
        if len(labels) > MAX_MAPS:
            raise ValueError(f"{path} : trop de cartes")
    if not labels or len({label for _, _, label in labels}) != len(labels):
        raise ValueError(f"{path} : cartes absentes ou répétées")
    return labels
