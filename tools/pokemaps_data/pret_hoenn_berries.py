"""Baies initialement plantées, lues dans les scripts de nouvelle partie Hoenn."""

from __future__ import annotations

import re

from .pret_gen3 import Gen3PretRepo


def initial_berries(repo: Gen3PretRepo, version: str) -> dict[int, str]:
    text = repo.source_text("data/scripts/new_game.inc", version)
    constants = repo.offers[version].scripts.constants
    entries = re.findall(r"setberrytree\s+(\w+),\s*ITEM_TO_BERRY\((ITEM_\w+)\),\s*BERRY_STAGE_BERRIES", text)
    if not entries or len(entries) > 128:
        raise ValueError(f"{repo.root} : plantations initiales absentes ou trop nombreuses")
    result = {}
    for tree, item in entries:
        number = int(tree) if tree.isdecimal() else constants[tree]
        if number in result:
            raise ValueError(f"{repo.root} : plantation initiale répétée : {tree}")
        result[number] = item
    return result
