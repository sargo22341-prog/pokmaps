"""Baies et Super Concours lus séparément dans les deux moteurs DS épinglés."""

from __future__ import annotations

import re
from pathlib import Path

from .pret_gen4_source import metang_enum, read_json, read_text

_FLAVORS = ("spiciness", "dryness", "sweetness", "bitterness", "sourness")
_DP_FLAVORS = ("spicy", "dry", "sweet", "bitter", "sour")
CATEGORIES = frozenset({"COOL", "BEAUTY", "CUTE", "SMART", "TOUGH"})


def berries(root: Path, platinum: bool) -> list[dict]:
    if platinum:
        paths = sorted((root / "res/items/data").glob("*_berry.json"))
        if len(paths) != 64:
            raise ValueError(f"{root} : 64 baies attendues")
        return [_berry(path.stem.replace("_", "-"), read_json(path)["berryData"]) for path in paths]
    rows = read_json(root / "files/itemtool/itemdata/nuts_data.json")["nuts_data"]
    if len(rows) != 64:
        raise ValueError(f"{root} : 64 baies attendues")
    return [
        _berry(
            row["name"].lower().replace("_", "-"),
            {
                "baseYield": row["yieldCategory"],
                "stageDuration": row["stageDuration"],
                "moistureDrainRate": row["unk5"],
                "smoothness": row["smoothness"],
                **dict(zip(_FLAVORS, (row[key] for key in _DP_FLAVORS), strict=True)),
            },
        )
        for row in rows
    ]


def _berry(identifier: str, value: dict) -> dict:
    return {
        "identifier": identifier,
        "stage_hours": value["stageDuration"],
        "min_yield": 2,
        "max_yield": value["baseYield"] * 5,
        "drain_rate": value["moistureDrainRate"],
        "smoothness": value["smoothness"],
        "flavors": [value[key] for key in _FLAVORS],
    }


def contests(root: Path, platinum: bool, effect_ids: dict[str, int]) -> list[dict]:
    if platinum:
        order = metang_enum(root / "generated/moves.txt")
        result = []
        for constant, number in order.items():
            if not 1 <= number <= 467:
                continue
            identifier = constant.removeprefix("MOVE_").lower()
            row = read_json(root / f"res/moves/{identifier}/data.json")["contest"]
            result.append(
                {
                    "id": number,
                    "category": row["type"].removeprefix("CONTEST_TYPE_"),
                    "effect_id": effect_ids[row["effect"]],
                }
            )
    else:
        rows = read_json(root / "files/poketool/waza/waza_tbl.json")["waza_tbl"]
        if len(rows) != 471 or [row["name"] for row in rows[468:]] != [f"MOVE_{i}" for i in range(468, 471)]:
            raise ValueError(f"{root} : emplacements réservés des attaques DS inconnus")
        result = [
            {"id": number, "category": row["contestType"], "effect_id": row["unkC"]}
            for number, row in enumerate(rows)
            if 1 <= number <= 467
        ]
    if len(result) != 467 or {row["id"] for row in result} != set(range(1, 468)):
        raise ValueError(f"{root} : Super Concours incomplets")
    if any(row["category"] not in CATEGORIES or not 1 <= row["effect_id"] <= 23 for row in result):
        raise ValueError(f"{root} : Super Concours : catégorie ou effet inconnu")
    return result


def contest_appeals(root: Path) -> dict[int, int]:
    if (root / "arm9").is_dir():
        text = read_text(root / "arm9/asm/unk_020828BC.s")
        body = text.split("UNK_020FBC68:", 1)[1].split("\n\t.text", 1)[0]
        raw = bytes(
            int(value, 16)
            for line in body.splitlines()
            if line.strip().startswith(".byte")
            for value in re.findall(r"0x([\da-fA-F]{2})\b", line)
        )
        if len(raw) != 24 * 26:
            raise ValueError(f"{root} : effets de Super Concours incomplets")
        result = {number: raw[number * 26 + 4] // 10 for number in range(1, 24)}
    else:
        result = _platinum_appeals(root)
    if set(result) != set(range(1, 24)) or any(not 0 <= value <= 4 for value in result.values()):
        raise ValueError(f"{root} : attrait des Super Concours illisible")
    return result


def _platinum_appeals(root: Path) -> dict[int, int]:
    ids = metang_enum(root / "generated/move_contest_effects.txt")
    text = read_text(root / "src/unk_02094EDC.c")
    pattern = r"\[(CONTEST_EFFECT_\w+)\]\s*=\s*\{\s*\w+,\s*\w+,\s*(0x[0-9a-fA-F]+|\d+)\s*,"
    result = {ids[name]: int(value, 0) // 10 for name, value in re.findall(pattern, text) if ids[name] != 0}
    return result
