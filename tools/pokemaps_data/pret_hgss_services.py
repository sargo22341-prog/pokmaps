"""Stocks, tarifs et transformations HGSS, avec étapes natives des services."""

import csv
import re
from pathlib import Path

from .pret_gen4_source import read_text
from .pret_hgss_scripts import Script
from .pret_hgss_trainers import item_constants


def shop_catalog(root: Path) -> dict:
    source = "src/scrcmd_mart.c"
    text = read_text(root / source)
    items = item_constants(root)
    prices = _prices(root)
    badge_body = text.split("_020FBF22[] = {", 1)[1].split("};", 1)[0]
    minimum_badges = {1: 0, 2: 1, 3: 3, 4: 5, 5: 7, 6: 8}
    ordinary = [
        dict(item=items[name], price=prices[items[name]], currency="money", minimum_badges=minimum_badges[int(tier)])
        for name, tier in re.findall(r"\{\s*(ITEM_\w+),\s*(\d+)\s*\}", badge_body)
    ]
    arrays = dict(re.findall(r"const u16 (_\w+)\[\] = \{([^{}]+)\};", text))
    order = text.split("*_0210FA3C[] = {", 1)[1].split("};", 1)[0]
    stocks = []
    for index, key in enumerate(re.findall(r"_\w+", order)):
        names = re.findall(r"ITEM_\w+", arrays[key])
        stocks.append(
            dict(
                index=index,
                native_array=key,
                items=[dict(item=items[name], price=prices[items[name]], currency="money") for name in names],
            )
        )
    if len(ordinary) != 19 or len(stocks) != 30:
        raise ValueError("HGSS : stocks ordinaires ou spéciaux incomplets")
    return dict(source=source, prices_source="files/itemtool/itemdata/item_data.csv", ordinary=ordinary, special=stocks)


def _prices(root: Path) -> dict[int, int]:
    items = item_constants(root)
    path = root / "files/itemtool/itemdata/item_data.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for row in rows:
        number, price = items[row["item"]], int(row["price"])
        if number in result or not 0 <= price <= 65535:
            raise ValueError(f"{path} : tarif invalide : {row['item']}")
        result[number] = price
    return result


def tutor_catalog(root: Path) -> list[dict]:
    source = "src/field/scrcmd_move_tutor.c"
    body = read_text(root / source).split("sTutorMoves[] = {", 1)[1].split("};", 1)[0]
    rows = [
        dict(move=move, cost=int(cost), currency="battle_points" if int(cost) else "free", npc=npc, source=source)
        for move, cost, npc in re.findall(r"\{\s*(MOVE_\w+),\s*(\d+),\s*(MOVE_TUTOR_NPC_\w+)\s*\}", body)
    ]
    if len(rows) != 52 or len({row["move"] for row in rows}) != len(rows):
        raise ValueError(f"HGSS : table des tuteurs inattendue : {len(rows)}")
    return rows


def apricorn_catalog(root: Path) -> dict:
    trees_source = "src/apricorn_tree_sys.c"
    body = read_text(root / trees_source).split("sTreeApricorns[NUM_APRICORN_TREE] = {", 1)[1].split("};", 1)[0]
    colors = re.findall(r"APRICORN_\w+", body)
    conversion_source = "asm/unk_02031B0C.s"
    body = read_text(root / conversion_source).split("_020F68D0:", 1)[1].split("_020F68DE:", 1)[0]
    balls = re.findall(r"ITEM_\w+", body)
    if len(colors) != 31 or len(balls) != 7:
        raise ValueError("HGSS : arbres ou conversions de Noigrumes incomplets")
    ordered = ("RED", "YLW", "BLU", "GRN", "PNK", "WHT", "BLK")
    items = item_constants(root)
    return dict(
        trees=[dict(index=i, color=color) for i, color in enumerate(colors)],
        trees_source=trees_source,
        conversions=[
            dict(color=f"APRICORN_{color}", item=items[ball], input_quantity=1, output_quantity=1)
            for color, ball in zip(ordered, balls, strict=True)
        ],
        conversion_source=conversion_source,
        delay_fr="Remise le jour suivant, après la levée du drapeau quotidien ; pas un délai fixe de 24 heures.",
        delay_source="src/unk_02055418.c",
        script_bank=874,
        daily_flag="FLAG_DAILY_KURT_MAKING_BALLS",
    )


def service_steps(scripts: dict[int, Script]) -> list[dict]:
    commands = frozenset(
        (
            "GiveItem",
            "GiveItemNoCheck",
            "TakeItem",
            "MartBuy",
            "SpecialMartBuy",
            "GiveMon",
            "GiveEgg",
            "GiveTogepiEgg",
            "GiveLoanMon",
            "LoadNPCTrade",
            "MoveTutorInit",
            "MoveTutorChooseMove",
            "TutorMoveTeachInSlot",
            "TutorMoveGetPrice",
            "GiveDaycareEgg",
            "GiveApricornFromTree",
            "ClearKurtApricorn",
            "ScrCmd_739",
            "HealParty",
            "TakeMoney",
            "GiveMoney",
            "TakeCoins",
            "GiveCoins",
        )
    )
    standard = frozenset(
        (
            "std_obtain_item_verbose",
            "std_give_item_verbose",
            "std_daycare_man",
            "std_daycare_lady",
            "std_nurse_joy",
            "std_frontier_move_tutor_1",
            "std_frontier_move_tutor_2",
            "std_frontier_move_tutor_3",
            "std_apricorn_tree",
        )
    )
    result = []
    for bank, script in scripts.items():
        for index, step in enumerate(script.steps):
            if step.command not in commands and not (step.command == "CallStd" and step.arguments[0] in standard):
                continue
            result.append(
                dict(
                    bank=bank,
                    instruction=index,
                    source=script.source,
                    line=step.line,
                    command=step.command,
                    arguments=step.arguments,
                )
            )
    return result
