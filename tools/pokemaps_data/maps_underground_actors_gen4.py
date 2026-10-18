"""Positions des marchands du Souterrain fixées par son script d'entrée."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pret_gen4_source import read_json

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header


def underground_positions(repo: Gen4PretRepo, header: Gen4Header) -> dict[int, tuple[int, int]]:
    names: dict[str, int] = {}
    if repo.platinum:
        file = next(name for name, number in repo.names.archives["events"].items() if number == header.events)
        data = read_json(repo.root / f"res/field/events/{file}.json")
        names = {event["id"]: rank for rank, event in enumerate(data["object_events"])}
    command = "SetObjectEventPos" if repo.platinum else "ScrCmd_SetEventDefaultPosition"
    result = {}
    for step in repo.flows[header.scripts].steps.values():
        if step.command != command:
            continue
        local_id, x, z = step.arguments
        number = names.get(local_id) if isinstance(local_id, str) else local_id
        if number is None or not isinstance(x, int) or not isinstance(z, int):
            raise ValueError(f"{header.constant} : position de marchand illisible : {step.source}")
        if number in result and result[number] != (x, z):
            raise ValueError(f"{header.constant} : positions contradictoires du marchand {number}")
        result[number] = (x, z)
    if len(result) != 20:
        raise ValueError(f"{header.constant} : vingt marchands attendus, {len(result)} positions lues")
    return result
