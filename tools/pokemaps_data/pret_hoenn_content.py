"""Caractéristiques des baies et des décorations, sans valeurs des générations suivantes."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

FLAVORS = ("spicy", "dry", "sweet", "bitter", "sour")


@dataclass(frozen=True)
class Berry:
    identifier: str
    stage_hours: int
    min_yield: int
    max_yield: int
    smoothness: int
    flavors: tuple[int, ...]


def berries(root: Path) -> tuple[Berry, ...]:
    text = (root / "src/berry.c").read_text(encoding="utf-8").split("gBerries[]", 1)[1].split("};", 1)[0]
    result = []
    for body in re.findall(r"\{([^{}]+)\}", text, re.S):
        if ".stageDuration" not in body:
            continue
        fields = dict(re.findall(r"\.(\w+)\s*=\s*(\w+)", body))
        name = re.search(r"(?:NAME_|sBerryDescriptionPart1_)(\w+)", body)
        if name is None:
            raise ValueError(f"{root} : baie sans nom")
        identifier = name[1].removesuffix("_BERRY").lower() + "-berry"
        result.append(
            Berry(
                identifier,
                int(fields["stageDuration"]),
                int(fields["minYield"]),
                int(fields["maxYield"]),
                int(fields["smoothness"]),
                tuple(int(fields[key]) for key in FLAVORS),
            )
        )
    if len(result) not in {43, 44} or len({row.identifier for row in result}) != len(result):
        raise ValueError(f"{root} : table des baies incomplète")
    return tuple(result)


@dataclass(frozen=True)
class Decoration:
    identifier: str
    category: str
    shape: str
    permission: str
    price: int


def decorations(root: Path) -> tuple[Decoration, ...]:
    path = root / "src/data/decoration/header.h"
    result = []
    if path.is_file():
        for key, body in re.findall(r"\[(DECOR_\w+)\]\s*=\s*\{(.*?)\}", path.read_text(encoding="utf-8"), re.S):
            if key == "DECOR_NONE":
                continue
            fields = dict(re.findall(r"\.(\w+)\s*=\s*(\w+)", body))
            result.append(
                Decoration(key, fields["category"], fields["shape"], fields["permission"], int(fields["price"]))
            )
    else:
        text = (root / "src/decoration.c").read_text(encoding="utf-8").split("gDecorations[]", 1)[1]
        pattern = r'\{(DECOR_\w+),\s*_\("[^"]+"\),\s*(DECORPERM_\w+),\s*(DECORSHAPE_\w+),\s*(DECORCAT_\w+),\s*(\d+)'
        result = [
            Decoration(key, category, shape, permission, int(price))
            for key, permission, shape, category, price in re.findall(pattern, text)
            if key != "DECOR_NONE"
        ]
    if len(result) != 120 or len({row.identifier for row in result}) != 120:
        raise ValueError(f"{root} : 120 décorations uniques attendues")
    return tuple(result)


def berry_rows(root: Path, names: dict[str, str]) -> list[dict[str, object]]:
    return [{**asdict(row), "name": names[row.identifier]} for row in berries(root)]
