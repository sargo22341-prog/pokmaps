"""Réserves des quatre installations propres à Platine."""

from __future__ import annotations

import re
import struct
from pathlib import Path

from .pret_gen4_animation import narc_members
from .pret_gen4_engine_text import c_initializer
from .pret_gen4_source import metang_enum, read_binary, read_text


def frontier_catalog(root: Path) -> dict:
    trainers = metang_enum(root / "generated/frontier_trainers.txt")
    ranges = {}
    for facility in ("Castle", "Arcade", "Factory"):
        text = read_text(root / f"src/overlay104/battle_{facility.lower()}_helpers.c")
        body = c_initializer(text, f"sBattle{facility}OpponentPools", str(root))
        values = [trainers[key] for key in re.findall(r"FRONTIER_TRAINER_\w+", body)]
        if len(values) != 32:
            raise ValueError(f"{root} : {facility} : huit séries attendues")
        # Ces trois moteurs utilisent modulo (max - min), contrairement à la Tour.
        ranges[facility.lower()] = [
            {
                "series": i + 1,
                "ordinary": [values[i * 4], values[i * 4 + 1] - 1],
                "last": [values[i * 4 + 2], values[i * 4 + 3] - 1],
            }
            for i in range(8)
        ]
    return {"ranges": ranges, "factory": _factory(root), "hall": _hall(root)}


def _factory(root: Path) -> dict:
    text = read_text(root / "src/overlay104/battle_factory_helpers.c")
    trainers = metang_enum(root / "generated/frontier_trainers.txt")
    result = {}
    for key, name in (
        ("level50", "sLevel50Pools"),
        ("open_player", "sOpenLevelPlayerPools"),
        ("open_opponent", "sOpenLevelOpponentPools"),
    ):
        body = c_initializer(text, name, str(root))
        pattern = (
            r"\.trainerIDMax = (\w+),\s*\.setIDMin = (\d+),\s*\.setIDMax = (\d+),"
            r"\s*\.ivs = (\d+),\s*\.canBeUpgraded = (TRUE|FALSE)"
        )
        rows = [
            {
                "trainer_limit": trainers[limit],
                "min": int(low),
                "max": int(high),
                "ivs": int(ivs),
                "upgrade": upgrade == "TRUE",
            }
            for limit, low, high, ivs, upgrade in re.findall(pattern, body)
        ]
        if len(rows) != 10:
            raise ValueError(f"{root} : Usine : dix réserves attendues : {key}")
        result[key] = rows
    return result


def _hall(root: Path) -> dict:
    path = root / "res/prebuilt/battle/b_pl_stage/pl_bsdpm.narc"
    members = narc_members(read_binary(path), str(path))
    sets = []
    for number, data in enumerate(members):
        if len(data) != 16:
            raise ValueError(f"{path} : équipe {number} de taille inattendue")
        species, *values = struct.unpack("<5H2B2H", data)
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
    text = read_text(root / "src/overlay104/battle_hall_helpers.c")
    opponents = re.findall(r"SPECIES_\w+", c_initializer(text, "sBattleHallPotentialOpponents", str(root)))
    species_ids = metang_enum(root / "generated/species.txt")
    if len(sets) != 478 or [row["species"] for row in sets[1:]] != [species_ids[key] for key in opponents]:
        raise ValueError(f"{path} : index des adversaires du Castel incohérent")
    # Les bornes du moteur sont des indices de configuration à partir de 1.
    groups = {key: int(value) for key, value in re.findall(r"#define (GROUP_\d_START) (\d+)", text)}
    body = c_initializer(text, "sPotentialMatchupRangesByRank", str(root))
    bounds = []
    for low, high in re.findall(
        r"\{ (GROUP_\d_START), (GROUP_\d_START - 1|NELEMS\(sBattleHallPotentialOpponents\)) }", body
    ):
        end = len(opponents) if high.startswith("NELEMS") else groups[high.split()[0]] - 1
        bounds.append([groups[low], end])
    if len(bounds) != 10:
        raise ValueError(f"{root} : Castel : dix rangs attendus")
    return {"sets": sets[1:], "ranks": bounds}
