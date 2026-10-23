"""Équipes natives HGSS, avec attaques initialisées comme dans le moteur."""

import re
from pathlib import Path

from .pret_gen4_source import c_defines, read_json, read_text
from .pret_hgss_binary import read_archive
from .pret_hgss_pokemon import read_level_moves


def trainer_catalog(root: Path) -> list[dict]:
    source = "files/poketool/trainer/trainers.json"
    rows = read_json(root / source)["trainers"]
    constants = c_defines(root / "include/constants/trainers.h", "TRAINER_")
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    moves = c_defines(root / "include/constants/moves.h", "MOVE_")
    items = item_constants(root)
    levels = read_archive(root / "files/poketool/personal/wotbl.narc")
    if len(rows) != 738 or len(levels) != 508:
        raise ValueError("HGSS : 738 équipes et 508 listes d'attaques attendues")
    names = {number: name for name, number in constants.items()}
    result = []
    for index, row in enumerate(rows[1:], 1):
        if index not in names or set(row) != {
            "type",
            "class",
            "name",
            "items",
            "ai_flags",
            "double",
            "party",
            "messages",
        }:
            raise ValueError(f"HGSS : structure du dresseur {index} inconnue")
        if row["double"] not in (0, 2) or not 1 <= len(row["party"]) <= 6:
            raise ValueError(f"HGSS : taille ou mode du combat {index} invalide")
        result.append(
            dict(
                id=index,
                constant=names[index],
                source=source,
                native_name=row["name"],
                trainer_class=row["class"],
                double=row["double"] == 2,
                ai_flags=row["ai_flags"],
                items=[items[name] for name in row["items"]],
                party=[_pokemon(mon, row["type"], species, moves, items, levels, index) for mon in row["party"]],
            )
        )
    return result


def item_constants(root: Path) -> dict[str, int]:
    text = read_text(root / "include/constants/items.h").split("#define ITEMS_COUNT", 1)[0]
    values = {name: int(value) for name, value in re.findall(r"^#define\s+(ITEM_\w+)\s+(\d+)\b", text, re.M)}
    for name, target in re.findall(r"^#define\s+(ITEM_\w+)\s+(ITEM_\w+)\b", text, re.M):
        values[name] = values[target]
    if values.get("ITEM_POTION") != 17 or values.get("ITEM_BLUE_ORB") != 535:
        raise ValueError("HGSS : constantes d'objets absentes")
    return values


def _pokemon(
    mon: dict,
    kind: str,
    species: dict[str, int],
    moves: dict[str, int],
    items: dict[str, int],
    levels: tuple[bytes, ...],
    trainer: int,
) -> dict:
    formats = {
        "TRTYPE_MON": (False, False),
        "TRTYPE_MON_MOVES": (True, False),
        "TRTYPE_MON_ITEM": (False, True),
        "TRTYPE_MON_ITEM_MOVES": (True, True),
    }
    if kind not in formats or ("moves" in mon, "item" in mon) != formats[kind]:
        raise ValueError(f"HGSS : format d'équipe inconnu pour {trainer} : {kind}")
    number, level = species[mon["species"]], mon["level"]
    if not 1 <= number <= 493 or not 1 <= level <= 100 or not 0 <= mon["difficulty"] <= 255:
        raise ValueError(f"HGSS : Pokémon invalide dans l'équipe {trainer}")
    if "moves" in mon:
        attacks = [moves[name] for name in mon["moves"]]
    else:
        attacks = default_attacks(read_level_moves(levels[number], f"wotbl/{number}"), level)
    if not 1 <= len(attacks) <= 4 or any(not 0 <= move <= 467 for move in attacks):
        raise ValueError(f"HGSS : attaques invalides dans l'équipe {trainer}")
    return dict(
        species=number,
        level=level,
        form=mon.get("form", 0),
        moves=attacks,
        custom_moves="moves" in mon,
        item=items[mon.get("item", "ITEM_NONE")],
        difficulty=mon["difficulty"],
        gender=mon["genderOverride"],
        ability=mon["abilityOverride"],
        capsule=mon["capsule"],
    )


def default_attacks(learnset: tuple[tuple[int, int], ...], level: int) -> list[int]:
    attacks: list[int] = []
    for required, move in learnset:
        if required <= level and move not in attacks:
            attacks.append(move)
            attacks = attacks[-4:]
    return attacks
