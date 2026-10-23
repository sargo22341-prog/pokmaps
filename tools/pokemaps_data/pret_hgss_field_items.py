"""Objets de terrain HGSS : tables cachées et scripts communs des Poké Balls."""

import re
from pathlib import Path

from .pret_gen4_source import read_text
from .pret_hgss_scripts import Script
from .pret_hgss_trainers import item_constants


def field_item_tables(root: Path, scripts: dict[int, Script]) -> dict[str, dict]:
    constants = {
        name: int(value)
        for name, value in re.findall(
            r"^#define\s+(std_\w+)\s+(\d+)\b", read_text(root / "include/constants/std_script.h"), re.M
        )
    }
    items = item_constants(root)
    text = read_text(root / "src/data/fieldmap/hidden_items.h")
    pattern = r"\{\s*(ITEM_\w+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\}"
    hidden = {}
    for name, quantity, unknown2, unknown3, index in re.findall(pattern, text):
        key = 8000 + int(index)
        if key in hidden or int(quantity) < 1:
            raise ValueError(f"HGSS : objet caché invalide ou répété : {key}")
        hidden[key] = dict(
            item=items[name],
            quantity=int(quantity),
            native_fields=[int(unknown2), int(unknown3)],
            source="src/data/fieldmap/hidden_items.h",
            index=int(index),
            kind="hidden",
        )
    visible = _visible_items(scripts[141])
    result = {}
    for name, number in constants.items():
        if name == "std_itemball_variadic":
            result[name] = dict(
                script=number,
                kind="visible_variable",
                source=scripts[141].source,
                item_variable="VAR_SPECIAL_x8008",
                quantity_variable="VAR_SPECIAL_x8009",
            )
        elif name.startswith("std_itemball_"):
            result[name] = visible[number - 7000] | dict(script=number)
        elif name.startswith("std_hiddenitem_"):
            result[name] = hidden[number] | dict(script=number)
    if len(visible) != 255 or len(hidden) != 231:
        raise ValueError(f"HGSS : tables d'objets inattendues : {len(visible)} visibles, {len(hidden)} cachés")
    return result


def _visible_items(script: Script) -> dict[int, dict]:
    result = {}
    for index, entry in enumerate(script.entries[:-1]):
        start = script.labels[entry]
        first, second = script.steps[start : start + 2]
        if first.command != "SetVar" or second.command != "SetVar":
            raise ValueError(f"HGSS : script d'objet {index} sans paramètres")
        if first.arguments[0] != "VAR_SPECIAL_x8008" or second.arguments[0] != "VAR_SPECIAL_x8009":
            raise ValueError(f"HGSS : registres d'objet inconnus : {index}")
        item, quantity = int(first.arguments[1], 0), int(second.arguments[1], 0)
        if not 1 <= item <= 535 or not 1 <= quantity <= 999:
            raise ValueError(f"HGSS : objet ou quantité hors limite : {index}")
        result[index] = dict(item=item, quantity=quantity, kind="visible", source=script.source, entry=entry)
    return result
