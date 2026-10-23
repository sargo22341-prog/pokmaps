"""Offres quotidiennes et Cartes Mémo HGSS, tarifs en Points Athlète natifs."""

import re
from pathlib import Path

from .pret_gen4_source import read_text
from .pret_hgss_flow_context import read_constants
from .pret_hgss_trainers import item_constants


def athlete_shop_catalog(root: Path) -> dict:
    source = "src/scrcmd_mart.c"
    text = read_text(root / source)
    items = item_constants(root)
    arrays = {}
    for name, body in re.findall(r"const struct MartItem (\w+)\[\] = \{([^{}]*(?:\{[^{}]*\}[^{}]*)+)\};", text):
        rows = [
            dict(item=items[item], cost=int(cost), currency="athlete_points", quantity=1)
            for item, cost in re.findall(r"\{\s*(ITEM_\w+),\s*(\d+)\s*\}", body)
        ]
        arrays[name] = rows
    daily = []
    for name, rows in arrays.items():
        if not name.startswith("sPokeathlonPrizeExchangePriceOverrides_"):
            continue
        suffix = name.removeprefix("sPokeathlonPrizeExchangePriceOverrides_")
        daily.append(
            dict(
                weekday=suffix.split("_")[0].upper(),
                national=suffix.endswith("_NatDex"),
                items=rows,
                limit_per_item_per_day=1,
                source=source,
                native_array=name,
            )
        )
    order = text.split("*_0210F9D4[] = {", 1)[1].split("};", 1)[0]
    cards = [
        dict(stage=i, items=arrays[name], source=source, native_array=name)
        for i, name in enumerate(re.findall(r"_\w+", order))
    ]
    if len(daily) != 14 or sum(len(row["items"]) for row in cards) != 27:
        raise ValueError("HGSS : stocks du Pokéathlon ou Cartes Mémo incomplets")
    return dict(
        daily=daily,
        data_cards=cards,
        data_card_rule_fr="Le premier groupe de six Cartes Mémo incomplet détermine le stock proposé.",
        reset_source="src/unk_02055418.c",
        seals=_seal_shops(root, text),
    )


def _seal_shops(root: Path, text: str) -> list[dict]:
    constants = read_constants(root)
    arrays = dict(re.findall(r"const u16 (_\w+)\[\] = \{([^{}]+)\};", text))
    order = text.split("*_0210F9E8[] = {", 1)[1].split("};", 1)[0]
    rows = [
        dict(
            weekday=day,
            items=[
                dict(seal=constants[name], cost=100, currency="money", quantity=1)
                for name in re.findall(r"SEAL_\w+", arrays[array])
            ],
            source="src/scrcmd_mart.c",
            price_source="src/overlay_03/shop_menu.c",
        )
        for day, array in enumerate(re.findall(r"_\w+", order))
    ]
    if len(rows) != 7 or any(len(row["items"]) != 7 for row in rows):
        raise ValueError("HGSS : boutiques de Sceaux incomplètes")
    return rows
