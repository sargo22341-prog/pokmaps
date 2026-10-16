"""Liaisons DS : warps, destinations des scripts et passages dont la destination dépend du moteur."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .pret_gen4 import Gen4PretRepo
from .pret_gen4_map_models import Gen4Header
from .pret_gen4_script_binary import ScriptFile
from .pret_gen4_scripts import MacroCall, TextScriptFile
from .pret_gen4_source import read_text


@dataclass(frozen=True)
class Passage:
    source: int | None
    target: int | None
    kind: str
    x: int | None
    z: int | None
    target_x: int | None
    target_z: int | None
    evidence: str
    note: str = ""


def warps(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> tuple[Passage, ...]:
    result = []
    for index, header in headers.items():
        for number, warp in enumerate(repo.events[header.events].warp_events):
            matrix = repo.matrices[header.matrix]
            if not (0 <= warp.x < matrix.width * 32 and 0 <= warp.z < matrix.height * 32):
                raise ValueError(f"{header.constant} : warp hors de la matrice : {warp}")
            evidence = f"events:{header.events}:warp:{number}"
            if warp.destination_header == 4095:
                result.append(
                    Passage(
                        index,
                        None,
                        "dynamic",
                        warp.x,
                        warp.z,
                        None,
                        None,
                        evidence,
                        "Retour vers la destination mémorisée par le moteur (ascenseur).",
                    )
                )
                continue
            if warp.destination_header not in repo.headers:
                raise ValueError(f"{header.constant} : en-tête de destination inconnu : {warp.destination_header}")
            destination = repo.headers[warp.destination_header]
            arrivals = repo.events[destination.events].warp_events
            if warp.destination_warp >= len(arrivals):
                raise ValueError(f"{header.constant} : warp d'arrivée absent : {warp}")
            arrival = arrivals[warp.destination_warp]
            if destination.index not in headers:
                result.append(
                    Passage(
                        index,
                        destination.index,
                        "unused",
                        warp.x,
                        warp.z,
                        arrival.x,
                        arrival.z,
                        evidence,
                        "Porte ancienne vers un en-tête écarté.",
                    )
                )
                continue
            result.append(Passage(index, destination.index, "warp", warp.x, warp.z, arrival.x, arrival.z, evidence))
    return tuple(result)


def scripted_passages(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> tuple[Passage, ...]:
    constants = {header.constant: index for index, header in repo.headers.items()}
    boats = _boat_macros(repo) if repo.platinum else {}
    result = []
    for index, header in headers.items():
        script = repo.scripts[header.scripts]
        if isinstance(script, TextScriptFile):
            result.extend(_platinum(index, header.scripts, script, constants, boats))
        elif isinstance(script, ScriptFile):
            result.extend(_diamond(index, header.scripts, script))
    return tuple(dict.fromkeys(result))


def _platinum(
    index: int | None, number: int, script: TextScriptFile, constants: dict[str, int], boats: dict
) -> list[Passage]:
    result = []
    for label, calls in script.labels.items():
        for call in calls:
            if call.name in boats or call.name == "PlayBoatCutscene":
                result.append(_boat_passage(index, number, call, boats, constants))
                continue
            if call.name not in ("Warp", "SetSpecialLocation", "WarpToColosseum"):
                continue
            args = call.arguments
            evidence = f"scripts:{number}:{label}:{call.line}:{call.name}"
            target = constants.get(args[0])
            coordinate = 1 if call.name == "Warp" else 2
            x, z = (_literal(value) for value in args[coordinate : coordinate + 2])
            if x is None or z is None:
                x, z = None, None
            note = "Destination conditionnée par le scénario ; branche non simulée."
            if target is None:
                note += " En-tête choisi dans une variable du script."
            kind = "elevator" if call.name == "SetSpecialLocation" else "script"
            result.append(Passage(index, target, kind, None, None, x, z, evidence, note))
    return result


def _diamond(index: int | None, number: int, script: ScriptFile) -> list[Passage]:
    result = []
    for call in script.instructions.values():
        if call.name not in ("ScrCmd_Warp", "ScrCmd_SetDynamicWarp", "ScrCmd_BattleRoomWarp", "ScrCmd_ShipAnimation"):
            continue
        if call.name == "ScrCmd_ShipAnimation":
            _, _, target, x, z = call.arguments
        else:
            target, _, x, z, _ = call.arguments
        kind = "elevator" if call.name == "ScrCmd_SetDynamicWarp" else "script"
        if call.name == "ScrCmd_ShipAnimation":
            kind = "boat"
        if target >= 0x4000:
            target = None
        x, z = (value if value < 0x4000 else None for value in (x, z))
        if x is None or z is None:
            x, z = None, None
        note = "Destination conditionnée par le scénario ; branche non simulée."
        result.append(
            Passage(index, target, kind, None, None, x, z, f"scripts:{number}:{call.offset}:{call.name}", note)
        )
    return result


def _literal(value: str) -> int | None:
    if value.isdecimal() or value.lower().startswith("0x"):
        integer = int(value, 0) if value.lower().startswith("0x") else int(value)
        return integer if 0 <= integer < 0x4000 else None
    return None


def _boat_macros(repo: Gen4PretRepo) -> dict:
    text = read_text(repo.root / "asm/macros/scrcmd.inc")
    result = {}
    for name, params, body in re.findall(r"\.macro (\w+)([^\n]*)\n(.*?)\.endm", text, re.DOTALL):
        expansion = re.search(r"^\s*PlayBoatCutscene ([^\n]+)", body, re.MULTILINE)
        if expansion:
            result[name] = (
                tuple(p.strip() for p in params.split(",") if p.strip()),
                tuple(p.strip() for p in expansion[1].split(",")),
            )
    if len(result) != 4:
        raise ValueError("scrcmd.inc : les quatre macros de bateau sont attendues")
    return result


def _boat_passage(index: int | None, number: int, call: MacroCall, boats: dict, constants: dict[str, int]) -> Passage:
    args = call.arguments
    if call.name in boats:
        parameters, expansion = boats[call.name]
        values = dict(zip(parameters, args, strict=True))
        args = tuple(values.get(value.removeprefix("\\"), value) for value in expansion)
    target = constants.get(args[2])
    if target is None:
        raise ValueError(f"bateau sans destination connue : {call}")
    return Passage(
        index,
        target,
        "boat",
        None,
        None,
        _literal(args[3]),
        _literal(args[4]),
        f"scripts:{number}:{call.line}:{call.name}",
        "Trajet en bateau après déblocage par le scénario.",
    )
