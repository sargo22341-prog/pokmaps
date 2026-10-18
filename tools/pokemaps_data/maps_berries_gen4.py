"""Baies déjà plantées à la création d'une partie DS, sans simuler la croissance."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .maps_offers_gen4 import item_identifier
from .pret_gen4_source import read_text
from .pret_models import NpcOffer

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .pret_gen4 import Gen4PretRepo


def initial_berries(repo: Gen4PretRepo) -> tuple[tuple[str, int], ...]:
    if repo.platinum:
        text = read_text(repo.root / "include/data/berry_init.h")
        rows = re.findall(r"\{\s*\.berryItemID\s*=\s*(ITEM_\w+),\s*\.yield\s*=\s*(\d+)\s*\}", text)
    else:
        text = read_text(repo.root / "arm9/overlays/52/src/overlay_52.c")
        body = text.split("const u16 ov52_021D76F8[] = {", 1)[1].split("};", 1)[0]
        rows = re.findall(r"(ITEM_\w+)\s*,\s*(\d+)\s*,", body)
    result = tuple((item, int(quantity)) for item, quantity in rows)
    if len(result) != 118 or any(not item.endswith("_BERRY") or not 1 <= count <= 5 for item, count in result):
        raise ValueError(f"{repo.root} : table des 118 plantations initiales illisible")
    return result


def berry_offers(builder: DatabaseBuilder, berries: tuple[tuple[str, int], ...], index: int) -> list[NpcOffer]:
    if not 0 <= index < len(berries):
        raise ValueError(f"Plantation DS inconnue : {index}")
    item, quantity = berries[index]
    return [
        NpcOffer(
            "fruit_tree",
            item_identifier(builder, item),
            None,
            None,
            None,
            None,
            None,
            None,
            stories=(
                f"Récolte initiale : {quantity} baie(s).",
                "Plantation présente au début de la partie ; après récolte, le sol permet de planter une baie.",
            ),
        )
    ]
