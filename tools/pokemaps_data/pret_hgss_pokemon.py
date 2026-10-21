"""Tables Pokémon HGSS natives, sans lecteur Sinnoh ni données modernes de remplacement."""

import re
import struct
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_source import read_json, read_text
from .pret_hgss_binary import read_archive


@dataclass(frozen=True)
class HgssPokemon:
    personal: tuple[dict, ...]
    level_moves: tuple[tuple[tuple[int, int], ...], ...]
    moves: tuple[dict, ...]
    machines: tuple[int, ...]
    tutors: tuple[dict, ...]
    evolutions: tuple[dict, ...]
    regional: tuple[int, ...]


def read_level_moves(data: bytes, where: str) -> tuple[tuple[int, int], ...]:
    if len(data) % 2 or not 2 <= len(data) <= 256:
        raise ValueError(f"{where} : taille de liste d'attaques invalide")
    values = struct.unpack(f"<{len(data) // 2}H", data)
    if 0xFFFF not in values:
        raise ValueError(f"{where} : terminaison d'attaques absente")
    end = values.index(0xFFFF)
    if values[end + 1 :] not in ((), (0,)):
        raise ValueError(f"{where} : données après la terminaison")
    rows = tuple((value >> 9, value & 511) for value in values[:end])
    if any(not 1 <= level <= 100 or not 1 <= move <= 467 for level, move in rows):
        raise ValueError(f"{where} : niveau ou attaque hors limites")
    return rows


def read_move(data: bytes, index: int) -> dict:
    if len(data) != 16:
        raise ValueError(f"waza_tbl membre {index} : 16 octets attendus")
    effect, category, power, kind, accuracy, pp, chance, target, priority, flags, contest, contest_type = struct.unpack(
        "<H6BHb3B2x", data
    )
    if category > 2 or kind > 17 or accuracy > 100 or not 1 <= pp <= 40:
        raise ValueError(f"waza_tbl membre {index} : caractéristiques invalides")
    return dict(
        id=index,
        effect=effect,
        damage_class=("physical", "special", "status")[category],
        power=power,
        type=kind,
        accuracy=accuracy,
        pp=pp,
        effect_chance=chance,
        target=target,
        priority=priority,
        flags=flags,
        contest_effect=contest,
        contest_type=contest_type,
    )


def read_hgss_pokemon(root: Path) -> HgssPokemon:
    personal = tuple(read_json(root / "files/poketool/personal/personal.json")["baseStats"])
    levels = read_archive(root / "files/poketool/personal/wotbl.narc")
    move_data = read_archive(root / "files/poketool/waza/waza_tbl.narc")
    if len(personal) != 508 or len(levels) != 508 or len(move_data) != 471:
        raise ValueError("HGSS : nombres de profils, listes d'attaques ou attaques inattendus")
    for index, row in enumerate(personal[1:494], 1):
        validate_personal(row, str(index))
    machine_text = read_text(root / "src/item.c").split("sTMHMMoves[] = {", 1)[1].split("};", 1)[0]
    constants = dict(re.findall(r"#define\s+(MOVE_\w+)\s+(\d+)", read_text(root / "include/constants/moves.h")))
    machines = tuple(int(constants[name]) for name in re.findall(r"\bMOVE_\w+", machine_text))
    if len(machines) != 100:
        raise ValueError("HGSS : 92 CT et 8 CS attendues")
    regional = read_archive(root / "files/poketool/johtozukan.narc")
    if len(regional) != 1 or len(regional[0]) != 988:
        raise ValueError("HGSS : table régionale invalide")
    ranks = struct.unpack("<494H", regional[0])
    if sorted(rank for rank in ranks if rank) != list(range(1, 257)):
        raise ValueError("HGSS : 256 rangs régionaux continus attendus")
    return HgssPokemon(
        personal,
        tuple(read_level_moves(data, f"wotbl/{i}") for i, data in enumerate(levels)),
        tuple(read_move(move_data[i], i) for i in range(1, 468)),
        machines,
        tuple(read_json(root / "files/fielddata/wazaoshie/waza_oshie.json")["tutor"]),
        tuple(read_json(root / "files/poketool/personal/evo.json")["evoTable"]),
        ranks,
    )


def validate_personal(row: dict, where: str) -> None:
    stats = ("hp", "atk", "def", "speed", "spatk", "spdef")
    if any(type(row[key]) is not int or not 1 <= row[key] <= 255 for key in stats):
        raise ValueError(f"HGSS {where} : statistiques personnelles invalides")
    if not 1 <= row["catchRate"] <= 255 or not 0 <= row["friendship"] <= 255:
        raise ValueError(f"HGSS {where} : capture ou bonheur invalide")
    for key, maximum in (("tms", 92), ("hms", 8)):
        if len(set(row[key])) != len(row[key]) or any(not 1 <= number <= maximum for number in row[key]):
            raise ValueError(f"HGSS {where} : compatibilité {key} invalide")
    for key in ("types", "abilities", "items", "eggGroups"):
        if len(row[key]) != 2:
            raise ValueError(f"HGSS {where} : paire {key} attendue")
