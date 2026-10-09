"""Schémas des fichiers JSON pret GBA ; un champ inconnu arrête la lecture."""

from __future__ import annotations

from typing import Any

_MAP_FIELDS = frozenset(
    [
        "id",
        "name",
        "layout",
        "music",
        "region_map_section",
        "requires_flash",
        "weather",
        "map_type",
        "allow_cycling",
        "allow_escaping",
        "allow_running",
        "show_map_name",
        "battle_scene",
        "floor_number",
        "connections",
        "connections_no_include",
        "object_events",
        "warp_events",
        "coord_events",
        "bg_events",
        "shared_events_map",
        "shared_scripts_map",
    ]
)
_LAYOUT_FIELDS = frozenset(
    [
        "id",
        "name",
        "width",
        "height",
        "primary_tileset",
        "secondary_tileset",
        "border_filepath",
        "blockdata_filepath",
        "border_width",
        "border_height",
    ]
)
_EVENT_FIELDS = {
    "object": frozenset(
        [
            "type",
            "x",
            "y",
            "elevation",
            "graphics_id",
            "local_id",
            "movement_type",
            "movement_range_x",
            "movement_range_y",
            "trainer_type",
            "trainer_sight_or_berry_tree_id",
            "script",
            "flag",
        ]
    ),
    "clone": frozenset(["type", "x", "y", "graphics_id", "target_local_id", "target_map"]),
    "trigger": frozenset(["type", "x", "y", "elevation", "var", "var_value", "script"]),
    "weather": frozenset(["type", "x", "y", "elevation", "weather"]),
    "sign": frozenset(["type", "x", "y", "elevation", "player_facing_dir", "script"]),
    "hidden_item": frozenset(["type", "x", "y", "elevation", "item", "flag", "quantity", "underfoot"]),
    "secret_base": frozenset(["type", "x", "y", "elevation", "secret_base_id"]),
    "warp": frozenset(["x", "y", "elevation", "dest_map", "dest_warp_id"]),
    "connection": frozenset(["map", "offset", "direction"]),
}


def validate_fields(row: object, allowed: frozenset[str], required: frozenset[str], where: str) -> None:
    if not isinstance(row, dict) or not required <= row.keys():
        raise ValueError(f"{where} : objet ou champs requis absents : {sorted(required)}")
    if unknown := row.keys() - allowed:
        raise ValueError(f"{where} : champs inconnus : {sorted(unknown)}")


def validate_layout(row: dict[str, Any], where: str) -> None:
    required = _LAYOUT_FIELDS - {"border_width", "border_height"}
    validate_fields(row, _LAYOUT_FIELDS, required, where)
    for field, value in row.items():
        expected = int if field in {"width", "height", "border_width", "border_height"} else str
        if type(value) is not expected:
            raise ValueError(f"{where} : type invalide pour {field}")


def validate_event(row: dict[str, Any], kind: str, where: str) -> None:
    if kind not in _EVENT_FIELDS:
        raise ValueError(f"{where} : type d’événement inconnu : {kind}")
    required = _EVENT_FIELDS[kind] - {"type", "local_id", "quantity", "underfoot"}
    validate_fields(row, _EVENT_FIELDS[kind], required, where)
    integers = {"x", "y", "elevation", "movement_range_x", "movement_range_y", "offset", "quantity"}
    for field, value in row.items():
        expected = int if field in integers else bool if field == "underfoot" else str
        if type(value) is not expected:
            raise ValueError(f"{where} : type invalide pour {field}")
        if field in {"x", "y", "offset"} and not -32768 <= value <= 32767:
            raise ValueError(f"{where} : coordonnées hors limites : {field}")
        if field in {"elevation", "movement_range_x", "movement_range_y"} and not 0 <= value <= 15:
            raise ValueError(f"{where} : valeur hors limites : {field}")


def validate_map(row: dict[str, Any], where: str) -> None:
    required = frozenset(
        [
            "id",
            "name",
            "layout",
            "music",
            "region_map_section",
            "requires_flash",
            "weather",
            "map_type",
            "allow_cycling",
            "allow_escaping",
            "allow_running",
            "show_map_name",
            "battle_scene",
        ]
    )
    required = required - {"allow_cycling", "allow_escaping", "allow_running"}
    validate_fields(row, _MAP_FIELDS, required, where)
    for field in required | (row.keys() & {"allow_cycling", "allow_escaping", "allow_running"}):
        expected = (
            bool
            if field in {"requires_flash", "allow_cycling", "allow_escaping", "allow_running", "show_map_name"}
            else str
        )
        if type(row[field]) is not expected:
            raise ValueError(f"{where} : type invalide pour {field}")
    types = {
        "MAP_TYPE_TOWN",
        "MAP_TYPE_CITY",
        "MAP_TYPE_ROUTE",
        "MAP_TYPE_INDOOR",
        "MAP_TYPE_UNDERGROUND",
        "MAP_TYPE_UNDERWATER",
        "MAP_TYPE_SECRET_BASE",
        "MAP_TYPE_OCEAN_ROUTE",
        "MAP_TYPE_6",
    }
    if row["map_type"] not in types:
        raise ValueError(f"{where} : type de carte inconnu : {row['map_type']}")
    for field in ("floor_number", "connections_no_include"):
        if field in row and type(row[field]) is not (int if field == "floor_number" else bool):
            raise ValueError(f"{where} : type invalide pour {field}")
    for field in ("shared_events_map", "shared_scripts_map"):
        if field in row and not isinstance(row[field], str):
            raise ValueError(f"{where} : nom de carte attendu pour {field}")
    _validate_map_events(row, where)


def _validate_map_events(row: dict[str, Any], where: str) -> None:
    for field in ("object_events", "warp_events", "coord_events", "bg_events", "connections"):
        events = row.get(field)
        if events is None and field == "connections":
            continue
        if events is None and field not in row:
            continue
        if not isinstance(events, list) or len(events) > 1024:
            raise ValueError(f"{where} : liste d’événements invalide : {field}")
        for event in events:
            if not isinstance(event, dict):
                raise ValueError(f"{where} : événement invalide : {field}")
            default = {"object_events": "object", "warp_events": "warp", "connections": "connection"}
            kind = event.get("type", default.get(field, ""))
            kinds = {
                "object_events": {"object", "clone"},
                "warp_events": {"warp"},
                "connections": {"connection"},
                "coord_events": {"trigger", "weather"},
                "bg_events": {"sign", "hidden_item", "secret_base"},
            }
            if kind not in kinds[field]:
                raise ValueError(f"{where} : type d’événement inconnu : {kind}")
            validate_event(event, kind, where)
