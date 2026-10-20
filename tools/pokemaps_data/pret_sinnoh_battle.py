"""Réserves d'équipes de la Tour et de la Zone de Combat, sans tirage de parcours."""

from __future__ import annotations

import re
import struct
from pathlib import Path

from .pret_gen4_engine_text import asm_data, c_initializer
from .pret_gen4_narc import members
from .pret_gen4_source import metang_enum, read_binary, read_json, read_text


def battle_catalog(root: Path, platinum: bool) -> dict:
    sets, trainers = _platinum(root) if platinum else _diamond(root)
    ranges = _ranges(root, platinum)
    if len(sets) != 951 or len(trainers) != (315 if platinum else 307):
        raise ValueError(f"{root} : catalogue de combat incomplet")
    for row in sets[1:]:
        if not (
            1 <= row["species"] <= 493
            and len(row["moves"]) == 4
            and all(0 <= move <= 467 for move in row["moves"])
            and 0 <= row["nature"] <= 24
            and 0 <= row["evs"] <= 63
            and 0 <= row["form"] <= 5
        ):
            raise ValueError(f"{root} : équipe invalide : {row}")
    for number, team in enumerate(trainers):
        if len(team) > 100 or any(not 1 <= item <= 950 for item in team):
            raise ValueError(f"{root} : réserve invalide du dresseur {number}")
    return {"sets": sets[1:], "trainers": trainers, "tower_ranges": ranges}


def _diamond(root: Path) -> tuple[list[dict], list[list[int]]]:
    directory = root / "files/battle/b_tower"
    if len(members(directory / "btdpm")) != 951 or len(members(directory / "btdtr")) != 307:
        raise ValueError(f"{root} : index des archives de combat incomplet")
    sets = []
    for number in range(951):
        path = directory / f"btdpm/narc_{number:04d}.bin"
        raw = read_binary(path, 16)
        if len(raw) != 16:
            raise ValueError(f"{path} : équipe DS de 16 octets attendue")
        species, *values = struct.unpack("<5H2B2H", raw)
        sets.append(
            {
                "id": number,
                "species": species,
                "moves": values[:4],
                "evs": values[4],
                "nature": values[5],
                "item": values[6],
                "form": values[7],
            }
        )
    trainers = []
    for number in range(307):
        path = directory / f"btdtr/narc_{number:04d}.bin"
        raw = read_binary(path, 204)
        if len(raw) < 4 or len(raw) % 2:
            raise ValueError(f"{path} : dresseur DS illisible")
        _, count = struct.unpack_from("<2H", raw)
        end = 4 + count * 2
        if len(raw) != (end + 3) // 4 * 4 or any(raw[end:]):
            raise ValueError(f"{path} : nombre d'équipes incohérent")
        trainers.append(list(struct.unpack_from(f"<{count}H", raw, 4)))
    return sets, trainers


def _platinum(root: Path) -> tuple[list[dict], list[list[int]]]:
    directory = root / "res/trainers/frontier"
    order = read_text(directory / "frontier_pokemon.order").splitlines()
    trainers = read_text(directory / "frontier_trainers.order").splitlines()
    if len(order) != 951 or len(trainers) != 315 or any(not re.fullmatch(r"\w+", key) for key in order + trainers):
        raise ValueError(f"{root} : index des équipes invalide")
    species = metang_enum(root / "generated/species.txt")
    moves = metang_enum(root / "generated/moves.txt")
    items = metang_enum(root / "generated/items.txt")
    natures = metang_enum(root / "generated/natures.txt")
    stats = ("hp", "attack", "defense", "speed", "special_attack", "special_defense")
    sets = []
    for number, key in enumerate(order):
        row = read_json(directory / f"pokemon/{key}.json")
        sets.append(
            {
                "id": number,
                "species": species[row["species"]],
                "moves": [moves[x] for x in row["moves"]],
                "evs": sum(1 << i for i, stat in enumerate(stats) if row["evFlags"][stat]),
                "nature": natures[row["nature"]],
                "item": items[row["item"]],
                "form": row["form"],
            }
        )
    ids = {key: number for number, key in enumerate(order)}
    pools = []
    for key in trainers:
        row = read_json(directory / f"data/{key}.json")
        pool = [ids[name] for name in row["availableSets"]]
        if 0 in pool[:-1]:
            raise ValueError(f"{root} : sentinelle au milieu d'une réserve : {key}")
        pools.append(pool[:-1] if pool and pool[-1] == 0 else pool)
    return sets, pools


def _ranges(root: Path, platinum: bool) -> list[dict]:
    if platinum:
        ids = metang_enum(root / "generated/frontier_trainers.txt")
        text = read_text(root / "src/unk_0204AEE8.c")
        values = [
            [ids[key] for key in re.findall(r"FRONTIER_TRAINER_\w+", c_initializer(text, name, str(root)))]
            for name in ("sBattleTowerTrainerRangesPerRoom", "sBattleTowerBossTrainerRangesPerRoom")
        ]
    else:
        text = read_text(root / "arm9/overlays/06/asm/overlay_06.s")
        values = []
        for first, following in (("ov06_02250C70", "ov06_02250C72"), ("ov06_02250C90", "ov06_02250C92")):
            raw = asm_data(text, first, str(root)) + asm_data(text, following, str(root))
            if len(raw) != 32:
                raise ValueError(f"{root} : plages des séries de combat illisibles")
            values.append(list(struct.unpack("<16H", raw)))
    if any(len(row) != 16 or any(not 0 <= number < 300 for number in row) for row in values):
        raise ValueError(f"{root} : plages des dresseurs invalides")
    return [
        {"series": i + 1, "ordinary": values[0][i * 2 : i * 2 + 2], "last": values[1][i * 2 : i * 2 + 2]}
        for i in range(8)
    ]
