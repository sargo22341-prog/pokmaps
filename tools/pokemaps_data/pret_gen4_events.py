"""Événements de Platine (res/field/events/*.json) : PNJ, warps, déclencheurs et panneaux, convertis en valeurs du
moteur comme le fait tools/jsoncnv/event.py, pour se comparer octet à octet aux fichiers compilés de
Diamant/Perle (pret_gen4_narc).
"""

from __future__ import annotations

from pathlib import Path

from .pret_gen4_map_models import BgEvent, CoordEvent, Gen4Events, ObjectEvent, WarpEvent
from .pret_gen4_maps import PlatinumNames, lookup
from .pret_gen4_source import read_json

_EVENT_KEYS = {
    "bg_events": frozenset({"script", "type", "x", "z", "y", "player_facing_dir"}),
    "object_events": frozenset(
        {
            "id",
            "clone_id",
            "graphics_id",
            "movement_type",
            "trainer_type",
            "hidden_flag",
            "script",
            "initial_dir",
            "data",
            "movement_range_x",
            "movement_range_z",
            "x",
            "z",
            "y",
            "double_battle_id",
        }
    ),
    "warp_events": frozenset({"x", "z", "dest_header_id", "dest_warp_id"}),
    "coord_events": frozenset({"script", "x", "z", "y", "width", "length", "var", "value"}),
}
# Scripts de dresseur des événements (tools/jsoncnv/convert.py, from_script) : identifiant - 1 + base.
_TRAINER_SCRIPT_BASE = {1: 3000, 2: 5000}
# Hauteur d'un PNJ : le JSON l'écrit en cases, le fichier compilé en fx32 (tools/jsoncnv/event.py).
_OBJECT_HEIGHT_UNIT = 0x10000


def read_events(root: Path, names: PlatinumNames) -> dict[int, Gen4Events]:
    enums = {
        "graphics": names.generated("object_events_gfx"),
        "movement": names.generated("movement_types"),
        "trainer_type": names.generated("trainer_types"),
        "facing": names.generated("bg_event_dirs"),
    }
    events = {}
    for name, index in names.archives["events"].items():
        path = root / f"res/field/events/{name}.json"
        data = read_json(path)
        if set(data) != set(_EVENT_KEYS):
            raise ValueError(f"{path} : clés d'événements inattendues")
        for kind, keys in _EVENT_KEYS.items():
            if unknown := [sorted(set(entry) - keys) for entry in data[kind] if set(entry) - keys]:
                raise ValueError(f"{path} : champs inconnus dans {kind} : {unknown}")
        events[index] = Gen4Events(
            index,
            tuple(_bg_event(entry, enums, str(path)) for entry in data["bg_events"]),
            tuple(_object_event(names, enums, entry, i, str(path)) for i, entry in enumerate(data["object_events"])),
            tuple(
                WarpEvent(e["x"], e["z"], lookup(names.map_headers, e["dest_header_id"], str(path)), e["dest_warp_id"])
                for e in data["warp_events"]
            ),
            tuple(_coord_event(names, entry, str(path)) for entry in data["coord_events"]),
        )
    return events


def _bg_event(entry: dict, enums: dict[str, dict[str, int]], where: str) -> BgEvent:
    facing = lookup(enums["facing"], entry["player_facing_dir"], where)
    return BgEvent(entry["script"], entry["type"], entry["x"], entry["z"], entry["y"], facing)


def _coord_event(names: PlatinumNames, entry: dict, where: str) -> CoordEvent:
    var = 0 if entry["var"] == "0" else lookup(names.vars_flags, entry["var"], where)
    e = entry
    return CoordEvent(e["script"], e["x"], e["z"], e["width"], e["length"], e["y"], e["value"], var)


def _object_event(
    names: PlatinumNames, enums: dict[str, dict[str, int]], entry: dict, index: int, where: str
) -> ObjectEvent:
    data = tuple(entry["data"])
    if len(data) > 3 or not all(isinstance(value, int) for value in data):
        raise ValueError(f"{where} : données de PNJ invalides : {data}")
    hidden = entry["hidden_flag"]
    if hidden == "0":
        hidden_flag = 0
    elif hidden in names.vars_flags:
        hidden_flag = names.vars_flags[hidden]
    else:
        hidden_flag = lookup(names.map_headers, hidden, where)
    return ObjectEvent(
        local_id=entry.get("clone_id", index),
        graphics=lookup(enums["graphics"], entry["graphics_id"], where),
        movement=lookup(enums["movement"], entry["movement_type"], where),
        trainer_type=lookup(enums["trainer_type"], entry["trainer_type"], where),
        hidden_flag=hidden_flag,
        script=_object_script(names, entry, where),
        direction=entry["initial_dir"],
        data=(*data, *(0,) * (3 - len(data))),
        range_x=entry["movement_range_x"],
        range_z=entry["movement_range_z"],
        x=entry["x"],
        z=entry["z"],
        y=entry["y"] * _OBJECT_HEIGHT_UNIT,
    )


def _object_script(names: PlatinumNames, entry: dict, where: str) -> int:
    script = entry["script"]
    if isinstance(script, int):
        return script
    battle = entry.get("double_battle_id", 1)
    if battle not in _TRAINER_SCRIPT_BASE:
        raise ValueError(f"{where} : combat double inconnu : {battle}")
    return lookup(names.trainers, script, where) - 1 + _TRAINER_SCRIPT_BASE[battle]
