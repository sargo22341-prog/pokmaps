"""Concours des deux moteurs Hoenn : catégories, cœurs et enchaînements."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContestMove:
    move: str
    effect: str
    category: str
    starter: str
    previous: tuple[str, ...]


def contest_moves(root: Path) -> tuple[ContestMove, ...]:
    text = (root / "src/data/contest_moves.h").read_text(encoding="utf-8").split("\n};", 1)[0]
    emerald = ".contestCategory" in text
    rows = _emerald_moves(text) if emerald else _ruby_moves(text)
    rows = tuple(row for row in rows if row.move != "NONE")
    if len(rows) != 354 or len({row.move for row in rows}) != 354:
        raise ValueError(f"{root} : concours : 354 attaques uniques attendues")
    return rows


def _emerald_moves(text: str) -> tuple[ContestMove, ...]:
    result = []
    for move, body in re.findall(r"\[MOVE_(\w+)\]\s*=\s*\{(.*?)\}", text, re.S):
        if move == "NONE":
            continue
        fields = dict(re.findall(r"\.(\w+)\s*=\s*(\w+)", body))
        # Émeraude initialise STOMP positionnellement après comboStarterId.
        combo = body.split(".comboMoves", 1)[1] if ".comboMoves" in body else body.split("{", 1)[1]
        previous = tuple(re.findall(r"COMBO_STARTER_(\w+)", combo))
        result.append(
            ContestMove(move, fields["effect"], fields["contestCategory"], fields["comboStarterId"], previous)
        )
    return tuple(result)


def _ruby_moves(text: str) -> tuple[ContestMove, ...]:
    pattern = r"\{(CONTEST_EFFECT_\w+),\s*(CONTEST_CATEGORY_\w+),\s*(\w+),\s*\{([^}]+)\}\},\s*// (\w+)"
    return tuple(
        ContestMove(move, effect, category, starter, tuple(re.findall(r"COMBO_STARTER_(\w+)", previous)))
        for effect, category, starter, previous, move in re.findall(pattern, text)
    )


def contest_effects(root: Path) -> dict[str, tuple[int, int]]:
    text = (root / "src/data/contest_moves.h").read_text(encoding="utf-8").split("gContestEffects[]", 1)[1]
    result = {}
    if ".appeal" in text:
        for effect, body in re.findall(r"\[(CONTEST_EFFECT_\w+)\]\s*=\s*\{(.*?)\}", text, re.S):
            fields = dict(re.findall(r"\.(appeal|jam)\s*=\s*(\d+)", body))
            result[effect] = (int(fields["appeal"]) // 10, int(fields["jam"]) // 10)
    else:
        for appeal, jam, effect in re.findall(r"\{\d+,\s*(\d+),\s*(\d+)\s*\},?\s*// (CONTEST_EFFECT_\w+)", text):
            result[effect] = (int(appeal) // 10, int(jam) // 10)
    if len(result) != 48:
        raise ValueError(f"{root} : concours : 48 effets attendus")
    return result
