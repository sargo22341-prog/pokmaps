"""Lecture indépendante des réserves HGSS ; aucune prédiction de tirage."""

import re
import struct
from pathlib import Path

from .pret_gen4_animation import narc_members
from .pret_gen4_engine_text import asm_data, c_initializer
from .pret_gen4_source import read_binary, read_text


def frontier_catalog(root: Path) -> dict:
    source = read_text(root / "asm/overlay_80_0222BDF4.s")
    hall_ranges = list(struct.iter_unpack("<2H", asm_data(source, "ov80_0223C5E0", str(root))))
    if len(hall_ranges) != 10:
        raise ValueError("HGSS : dix rangs de la Scène attendus")
    return dict(
        sets=_sets(root, "files/a/2/0/3", 951),
        trainers=_trainers(root),
        tower_ranges=_tower(root),
        frontier=dict(
            ranges={
                key: _ranges(root, file, label)
                for key, file, label in (
                    ("factory", "overlay_80_0222BDF4.s", "ov80_0223C478"),
                    ("castle", "overlay_80_02237A70.s", "ov80_0223D4D4"),
                    ("arcade", "overlay_80_02238034.s", "ov80_0223D514"),
                )
            },
            factory={
                key: _rentals(source, label, root)
                for key, label in (
                    ("level50", "ov80_0223C508"),
                    ("open_player", "ov80_0223C4B8"),
                    ("open_opponent", "ov80_0223C558"),
                )
            },
            hall=dict(sets=_sets(root, "files/a/2/0/4", 478), ranks=[list(r) for r in hall_ranges]),
        ),
    )


def _sets(root: Path, relative: str, count: int) -> list[dict]:
    path = root / relative
    entries = narc_members(read_binary(path), str(path))
    if len(entries) != count or any(len(row) != 16 for row in entries):
        raise ValueError(f"HGSS : archive de configurations incorrecte : {relative}")
    rows = []
    for number, raw in enumerate(entries[1:], 1):
        species, *values = struct.unpack("<5H2B2H", raw)
        rows.append(
            dict(
                id=number,
                species=species,
                moves=values[:4],
                evs=values[4],
                nature=values[5],
                item=values[6],
                form=values[7],
            )
        )
    return rows


def _trainers(root: Path) -> list[list[int]]:
    path = root / "files/a/2/0/2"
    entries = narc_members(read_binary(path), str(path))
    if len(entries) != 315:
        raise ValueError("HGSS : 315 réserves de dresseurs attendues")
    result = []
    for number, raw in enumerate(entries):
        if len(raw) < 4 or len(raw) % 4:
            raise ValueError(f"HGSS : réserve illisible : {number}")
        _, count = struct.unpack_from("<2H", raw)
        end = 4 + count * 2
        if not 0 <= count <= 100 or len(raw) != (end + 3) // 4 * 4 or any(raw[end:]):
            raise ValueError(f"HGSS : taille de réserve incorrecte : {number}")
        result.append(list(struct.unpack_from(f"<{count}H", raw, 4)))
    return result


def _tower(root: Path) -> list[dict]:
    text = read_text(root / "src/unk_0204B538.c")
    tables = [
        [list(map(int, r)) for r in re.findall(r"\{\s*(\d+),\s*(\d+)\s*}", c_initializer(text, key, str(root)))]
        for key in ("FrontierTrainerDifficultyBracket", "FrontierTrainerBracketBosses")
    ]
    if any(len(table) != 8 for table in tables):
        raise ValueError("HGSS : huit séries de la Tour attendues")
    return [dict(series=i + 1, ordinary=tables[0][i], last=tables[1][i]) for i in range(8)]


def _ranges(root: Path, filename: str, label: str) -> list[dict]:
    text = read_text(root / "asm" / filename)
    # Les trois premières bornes ont chacune une étiquette ; la quatrième porte la suite.
    address = int(label.rsplit("_", 1)[1], 16)
    raw = b"".join(asm_data(text, f"ov80_{address + i:08X}", filename) for i in (0, 2, 4, 6))
    if len(raw) != 64:
        raise ValueError(f"HGSS : huit séries attendues : {filename}")
    rows = list(struct.iter_unpack("<4H", raw))
    return [dict(series=i + 1, ordinary=[a, b - 1], last=[c, d - 1]) for i, (a, b, c, d) in enumerate(rows)]


def _rentals(text: str, label: str, root: Path) -> list[dict]:
    raw = asm_data(text, label, str(root))
    if len(raw) != 80:
        raise ValueError(f"HGSS : dix réserves de location attendues : {label}")
    return [
        dict(trainer_limit=limit, min=low, max=high, ivs=ivs, upgrade=bool(upgrade))
        for limit, low, high, ivs, upgrade in struct.iter_unpack("<3H2B", raw)
    ]
