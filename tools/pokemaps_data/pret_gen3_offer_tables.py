"""Tables C des échanges, des tuteurs et des lots utilisés par les scripts GBA."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


@dataclass(frozen=True)
class InGameTrade:
    pokemon: str
    wanted: str
    item: str | None


def trade_table(repo: Gen3PretRepo, version: str) -> tuple[InGameTrade, ...]:
    relative = "src/trade.c" if repo.ruby else "src/data/ingame_trades.h" if repo.remake else "src/data/trade.h"
    # Les conditions C sans rapport avec les données (compilation C23) ne participent pas à cette table.
    text = repo.source_text(relative, version) if repo.remake else read_text(repo.root / relative)
    match = re.search(r"(?:const|static const) struct InGameTrade \w+\[\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not match:
        raise ValueError(f"{relative} : table des échanges absente")
    if repo.ruby:
        selected = re.fullmatch(r"\s*#if ENGLISH\s+(.*?)\s*#elif GERMAN\s+.*?\s*#endif\s*", match[1], re.S)
        if selected is None:
            raise ValueError(f"{relative} : variantes linguistiques des échanges à relire")
        body = selected[1]
    else:
        if "#" in match[1]:
            raise ValueError(f"{relative} : table des échanges conditionnelle à relire")
        body = match[1]
    entries = re.findall(r"\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", body, re.S)
    result = []
    for entry in entries:
        species = re.findall(r"SPECIES_\w+", entry)
        items = re.findall(r"ITEM_\w+", entry)
        if len(species) != 2 or len(items) != 1:
            raise ValueError(f"{relative} : échange illisible : {entry}")
        result.append(InGameTrade(species[0], species[1], items[0] if items[0] != "ITEM_NONE" else None))
    if not 1 <= len(result) <= 32:
        raise ValueError(f"{relative} : nombre d'échanges invalide")
    return tuple(result)


def tutor_moves(repo: Gen3PretRepo) -> tuple[str, ...]:
    if repo.ruby:
        return ()
    text = read_text(repo.root / "src/data/pokemon/tutor_learnsets.h")
    table = re.search(r"(?:g|s)TutorMoves\[TUTOR_MOVE_COUNT\]\s*=\s*\{([^{}]*)\}", text, re.S)
    if not table:
        raise ValueError(f"{repo.root} : table des tuteurs absente")
    moves = tuple(re.findall(r"\bMOVE_\w+", table[1]))
    if len(moves) not in {15, 30} or len(set(moves)) != len(moves):
        raise ValueError(f"{repo.root} : table des tuteurs invalide")
    return moves
