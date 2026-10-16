"""Effets des attaques DS : numéro d'effet du moteur, probabilité de l'effet secondaire, puissance et PP.

Les deux dépôts nomment autrement les mêmes effets (BATTLE_EFFECT_* en Platine, MOVE_EFFECT_* en
Diamant/Perle) : la clé commune est le numéro du moteur, écrit sur trois chiffres dans
tools/data/move_effects.csv. Un test vérifie que les deux numérotations désignent les mêmes effets. Le moteur
tire Random % 100 contre la probabilité (battle_lib.c), comme les jeux GBA.
"""

from __future__ import annotations

import re
from pathlib import Path

from .pret_gen4_source import metang_enum, read_json, read_text
from .pret_moves import PretMove

_DP_EFFECT = re.compile(r"^#define (MOVE_EFFECT_\w+)\s+(\d+)\b", re.MULTILINE)
# Trois entrées techniques suivent les attaques jouables dans la table de Diamant/Perle.
_DP_RESERVED = frozenset({"MOVE_NONE", "MOVE_468", "MOVE_469", "MOVE_470"})
_MAX_EFFECT = 0xFFFF


def effect_key(number: int) -> str:
    """Clé d'un effet dans move_effects.csv : son numéro de moteur sur trois chiffres."""
    if not 0 <= number <= _MAX_EFFECT:
        raise ValueError(f"numéro d'effet DS invalide : {number}")
    return f"{number:03d}"


def effect_names(root: Path) -> dict[int, str]:
    """Nom de chaque numéro d'effet dans le dépôt, pour les messages et les comparaisons."""
    if (root / "generated/move_battle_effects.txt").is_file():
        names = metang_enum(root / "generated/move_battle_effects.txt")
    else:
        names = {name: int(value) for name, value in _DP_EFFECT.findall(read_text(root / "include/constants/battle.h"))}
    by_number = {number: name for name, number in names.items()}
    if len(by_number) != len(names) or sorted(by_number) != list(range(len(names))):
        raise ValueError(f"{root} : numéros d'effets d'attaques répétés ou discontinus")
    return by_number


def read_gen4_moves(root: Path) -> list[PretMove]:
    if (root / "res/moves").is_dir():
        return _platinum(root)
    return _diamond_pearl(root)


def _platinum(root: Path) -> list[PretMove]:
    numbers = {name: number for number, name in effect_names(root).items()}
    moves = []
    for path in sorted((root / "res/moves").glob("*/data.json")):
        if path.parent.name == "none":
            continue
        data = read_json(path)
        effect = data["effect"]
        if set(effect) != {"type", "chance"} or effect["type"] not in numbers:
            raise ValueError(f"{path} : effet d'attaque illisible : {effect}")
        moves.append(_move(path.parent.name.upper(), numbers[effect["type"]], data, effect["chance"], str(path)))
    return moves


def _diamond_pearl(root: Path) -> list[PretMove]:
    numbers = {name: number for number, name in effect_names(root).items()}
    path = root / "files/poketool/waza/waza_tbl.json"
    moves = []
    for row in read_json(path)["waza_tbl"]:
        if row["name"] in _DP_RESERVED:
            continue
        if row["effect"] not in numbers:
            raise ValueError(f"{path} : effet inconnu pour {row['name']} : {row['effect']}")
        moves.append(
            _move(row["name"].removeprefix("MOVE_"), numbers[row["effect"]], row, row["effectChance"], str(path))
        )
    return moves


def _move(const: str, effect: int, data: dict, chance: object, where: str) -> PretMove:
    if not isinstance(chance, int) or not 0 <= chance <= 100:
        raise ValueError(f"{where} : probabilité invalide pour {const} : {chance}")
    power, pp = data["power"], data["pp"]
    if not isinstance(power, int) or not isinstance(pp, int):
        raise ValueError(f"{where} : puissance ou PP non entiers pour {const}")
    return PretMove(const, effect_key(effect), power, pp, chance_percent=chance if 0 < chance < 100 else None)
