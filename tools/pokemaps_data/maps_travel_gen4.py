"""Destinations de Vol et liaisons du Monde Distorsion, lues dans le moteur de chaque version."""

from __future__ import annotations

import re

from .maps_passages_gen4 import Passage
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_maps_dp import _labelled_bytes
from .pret_gen4_source import ByteReader, read_text


def underground_connections(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    if repo.platinum:
        path = "src/field_map_change.c"
        source = read_text(repo.root / path).split("MapChangeUndergroundContext *MapChangeUndergroundContext_New", 1)[1]
        source = source.split("void FieldTask_SetUndergroundMapChange", 1)[0]
        if "ctx->mapHeaderID = MAP_HEADER_UNDERGROUND;" not in source or "location->mapHeaderID" not in source:
            raise ValueError(f"{path} : entrée ou retour du Souterrain modifié")
    else:
        path = "arm9/asm/unk_02048904.s"
        source = read_text(repo.root / path).split("sub_0204976C:", 1)[1].split("thumb_func_end", 1)[0]
        if re.search(r"mov r0, #0x2\s+str r0, \[r5, #0x8\]", source) is None:
            raise ValueError(f"{path} : entrée du Souterrain modifiée")
        if "LocalFieldData_GetDynamicWarp" not in source:
            raise ValueError(f"{path} : retour du Souterrain absent")
    header = repo.headers[2]
    expected = "MAP_HEADER_UNDERGROUND" if repo.platinum else "MAP_UNDERGROUND"
    if header.constant != expected:
        raise ValueError(f"{path} : en-tête du Souterrain modifié")
    return (
        Passage(
            None,
            2,
            "script",
            None,
            None,
            None,
            None,
            path,
            "Kit Explorateur depuis la surface autorisée ; arrivée calculée selon la position du joueur.",
        ),
        Passage(
            2,
            None,
            "dynamic",
            None,
            None,
            None,
            None,
            path,
            "Remontée vers la position de surface mémorisée par le moteur.",
        ),
    )


def fly_destinations(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    if repo.platinum:
        path = "src/spawn_locations.c"
        text = read_text(repo.root / path).split("sSpawnLocations[] = {", 1)[1].split("};", 1)[0]
        constants = {header.constant: index for index, header in repo.headers.items()}
        rows = re.findall(r"\{\s*(MAP_HEADER_\w+),\s*(\w+),\s*(\w+),\s*(MAP_HEADER_\w+),\s*(\w+),\s*(\w+),", text)
        targets = [(constants[row[3]], int(row[4], 0), int(row[5], 0)) for row in rows]
    else:
        path = "arm9/asm/unk_02034E84.s"
        text = read_text(repo.root / path).split("UNK_020F2224:", 1)[1].split(".text", 1)[0]
        rows = re.findall(r"\.short\s+([^\n]+)", text)
        values = [tuple(int(value.strip(), 0) for value in row.split(",")) for row in rows]
        if any(len(row) != 6 for row in values):
            raise ValueError(f"{path} : destination de Vol mal formée")
        targets = [(row[3], row[4], row[5]) for row in values]
    if len(targets) != 20 or any(target not in repo.headers for target, _, _ in targets):
        raise ValueError(f"{path} : table de Vol inattendue : {targets}")
    return tuple(
        Passage(
            None,
            target,
            "fly",
            None,
            None,
            x,
            z,
            f"{path}:{index}",
            "Depuis un lieu où Vol est autorisé, après déblocage de la destination.",
        )
        for index, (target, x, z) in enumerate(targets)
    )


def distortion_connections(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    if not repo.platinum:
        return ()
    path = "src/overlay009/ov9_02249960.c"
    text = read_text(repo.root / path)
    body = text.split("sDistWorldMapConnectionList[DISTORTION_WORLD_MAP_COUNT] = {", 1)[1].split("};", 1)[0]
    constants = {header.constant: index for index, header in repo.headers.items()}
    rows = re.findall(r"\.prevID = (\w+),\s*\.currID = (\w+),\s*\.nextID = (\w+)", body)
    if len(rows) != 10:
        raise ValueError(f"{path} : connexions du Monde Distorsion incomplètes")
    result = []
    for previous, current, following in rows:
        for target in (previous, following):
            if target == "MAP_HEADER_INVALID":
                continue
            result.append(
                Passage(
                    constants[current],
                    constants[target],
                    "platform",
                    None,
                    None,
                    None,
                    None,
                    path,
                    "Plateforme mobile ; gravité et déplacement du joueur non simulés.",
                )
            )
    return tuple(result)


def turnback_connections(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    if repo.platinum:
        path = "src/scrcmd.c"
        text = read_text(repo.root / path).split("static BOOL ScrCmd_InitTurnbackCave(ScriptContext *ctx)\n{", 1)[1]
        body = text.split("static const u16 pillarRooms[] = {", 1)[1].split("};", 1)[0]
        constants = {header.constant: index for index, header in repo.headers.items()}
        rooms = {constants[name] for name in re.findall(r"MAP_HEADER_\w+", body)}
        special = re.findall(r"destHeaderID = (MAP_HEADER_\w+);", text.split("u8 warpID", 1)[0])
        targets = rooms | {constants[name] for name in special}
    else:
        path = "arm9/asm/unk_02038C78.s"
        data = _labelled_bytes(repo.root / path, "UNK_020F3538")
        if len(data) != 36:
            raise ValueError(f"{path} : les 18 salles aléatoires de la Grotte Retour sont attendues")
        rooms = set(ByteReader(data, path).unpack("18H", 0))
        source = read_text(repo.root / "arm9/src/scrcmd.c").split("BOOL ScrCmd_Unk0285(ScriptContext *ctx)", 1)[1]
        special = {int(value) for value in re.findall(r"unk2 = (\d+);", source.split("u8 unk3", 1)[0])}
        targets = rooms | (special - {0})
    if len(rooms) != 18 or len(targets) != 21 or not targets <= repo.headers.keys():
        raise ValueError(f"{path} : destinations de la Grotte Retour incohérentes : {targets}")
    note = "Destination selon les piliers vus et les salles traversées ; tirage aléatoire non simulé."
    return tuple(
        Passage(source, target, "random_room", None, None, None, None, path, note)
        for source in sorted(targets)
        for target in sorted(targets)
    )
