"""Mobilier et pièges du Souterrain : prix et accès lus dans chaque moteur."""

from __future__ import annotations

import re
import struct
from pathlib import Path

from .pret_gen4_engine_text import asm_data, c_initializer
from .pret_gen4_source import metang_enum, read_text


def underground_catalog(root: Path, platinum_root: Path, platinum: bool) -> dict:
    goods_ids = metang_enum(platinum_root / "generated/goods.txt")
    trap_ids = metang_enum(platinum_root / "generated/traps.txt")
    spheres = metang_enum(platinum_root / "generated/sphere_types.txt") | {"RANDOM_SPHERE_TYPE": 6}
    if platinum:
        goods = _goods(root, goods_ids, spheres)
        traps = _traps(root, trap_ids, spheres)
    else:
        text = read_text(root / "arm9/asm/unk_0204CA80.s").split("\n\t.text", 1)[0]
        raw = bytes(
            int(value, 16)
            for line in text.splitlines()
            if line.strip().startswith(".byte")
            for value in re.findall(r"0x([\da-fA-F]{2})\b", line)
        )
        if len(raw) != 139 * 28:
            raise ValueError(f"{root} : mobilier DS incomplet")
        goods = [
            {
                "id": i,
                "width": raw[i * 28],
                "depth": raw[i * 28 + 1],
                "sphere": raw[i * 28 + 11],
                "min_size": raw[i * 28 + 12],
                "max_size": raw[i * 28 + 13],
                "national": bool(raw[i * 28 + 24]),
                "money": struct.unpack_from("<I", raw, i * 28 + 16)[0],
            }
            for i in range(139)
        ]
        text = read_text(root / "arm9/overlays/18/asm/overlay_18.s")
        raw = b"".join(
            asm_data(text, label, str(root)) for label in ("ov18_02250748", "ov18_02250749", "ov18_0225074A")
        )
        if len(raw) != 104 or raw[-2:] != b"\0\0":
            raise ValueError(f"{root} : prix des pièges DS illisibles")
        traps = [
            {"id": i, "sphere": raw[i * 3], "min_size": raw[i * 3 + 1], "max_size": raw[i * 3 + 2]} for i in range(34)
        ]
    return {
        "goods": [
            {**row, "identifier": key}
            for key, number in goods_ids.items()
            if 7 <= number < 139
            for row in goods
            if row["id"] == number
        ],
        "traps": [
            {**row, "identifier": key}
            for key, number in trap_ids.items()
            if 1 <= number < 34
            for row in traps
            if row["id"] == number and row["sphere"] != 0
        ],
    }


def _goods(root: Path, ids: dict[str, int], spheres: dict[str, int]) -> list[dict]:
    body = c_initializer(read_text(root / "src/goods.c"), "sGoodData", str(root))
    result = []
    pattern = r"\[(UG_GOOD_\w+)\]\s*=\s*\{(.*?)(?=\n    \[|\Z)"
    for key, block in re.findall(pattern, body, re.S):
        fields = dict(
            re.findall(r"\.(width|depth|sphereType|minSize|maxSize|natDexRequired|moneyPrice)\s*=\s*(\w+)", block)
        )
        result.append(
            {
                "id": ids[key],
                "width": int(fields["width"]),
                "depth": int(fields["depth"]),
                "sphere": spheres[fields["sphereType"]],
                "min_size": int(fields["minSize"]),
                "max_size": int(fields["maxSize"]),
                "national": fields["natDexRequired"] == "TRUE",
                "money": int(fields["moneyPrice"]),
            }
        )
    if len(result) != 139:
        raise ValueError(f"{root} : mobilier incomplet")
    return result


def _traps(root: Path, ids: dict[str, int], spheres: dict[str, int]) -> list[dict]:
    text = read_text(root / "src/underground/trap_prices.c")
    pattern = r"\[(TRAP_\w+)\]\s*=\s*\{\s*\.sphereType = (\w+), .minSize = (\d+), .maxSize = (\d+)"
    rows = [
        {"id": ids[key], "sphere": spheres[sphere], "min_size": int(low), "max_size": int(high)}
        for key, sphere, low, high in re.findall(pattern, text)
    ]
    if len(rows) != 34:
        raise ValueError(f"{root} : pièges incomplets")
    return rows
