"""Poids des objets enfouis, propres à chaque version, sans simulation de fouille."""

from __future__ import annotations

import re
import struct
from collections import defaultdict
from pathlib import Path

from .pret_gen4_engine_text import c_initializer
from .pret_gen4_source import c_enum, read_text


def mining_catalog(root: Path, platinum_root: Path, version: str) -> list[dict]:
    ids = c_enum(platinum_root / "include/underground/mining.h", "MiningObjectID")
    names = {number: key for key, number in ids.items() if key != "MINING_SPHERES_MAX"}
    rows = _platinum(root, ids) if version == "platinum" else _diamond(root)
    merged: dict[int, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for number, weights in rows:
        if not 1 <= number <= 66 or len(weights) != 4:
            raise ValueError(f"{root} : objet enfoui inconnu : {number}")
        if number >= ids["MINING_TREASURE_MAX"]:
            continue  # Les rochers sont des obstacles de fouille, pas des objets à obtenir.
        merged[number] = [a + b for a, b in zip(merged[number], weights, strict=True)]
    if len(merged) != 58:
        raise ValueError(f"{root} : catalogue de fouille incomplet : {len(merged)}")
    return [
        {"id": number, "identifier": names[number], "weights": weights} for number, weights in sorted(merged.items())
    ]


def _platinum(root: Path, ids: dict[str, int]) -> list[tuple[int, list[int]]]:
    text = read_text(root / "src/underground/mining.c")
    body = c_initializer(text, "sMiningObjects", str(root))
    pattern = (
        r"\.itemID\s*=\s*(MINING_\w+),\s*\.oddTIDWeight\s*=\s*(\d+),"
        r"\s*\.evenTIDWeight\s*=\s*(\d+),\s*\.oddTIDNatDexWeight\s*=\s*(\d+),"
        r"\s*\.evenTIDNatDexWeight\s*=\s*(\d+)"
    )
    rows = [(ids[key], list(map(int, weights))) for key, *weights in re.findall(pattern, body)]
    if len(rows) != 85:
        raise ValueError(f"{root} : table des formes d'objets enfouis illisible")
    return rows


def _diamond(root: Path) -> list[tuple[int, list[int]]]:
    text = read_text(root / "arm9/overlays/18/asm/overlay_18.s")
    body = text.split("ov18_02250B30: ;", 1)[1].split("ov18_022511D4:", 1)[0]
    data = bytearray()
    for line in body.splitlines():
        if match := re.match(r"\s*\.byte\s+(.+)", line):
            data.extend(int(value.strip(), 0) for value in match.group(1).split(","))
        elif match := re.match(r"\s*\.word\s+(\w+)", line):
            value = match.group(1)
            # Les pointeurs de formes sont inutiles aux poids ; leur emplacement reste conservé.
            data.extend((0 if value.startswith("ov18_") else int(value, 0)).to_bytes(4, "little"))
    if len(data) != 85 * 20:
        raise ValueError(f"{root} : table binaire des objets enfouis illisible")
    return [
        (data[offset + 14], list(struct.unpack_from("<4H", data, offset + 4))) for offset in range(0, len(data), 20)
    ]
