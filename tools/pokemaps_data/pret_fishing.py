"""Pêche de Rouge, Bleu et Jaune, lue dans pret.

La Canne donne toujours le même Pokémon (ItemUseOldRod) et la Super Canne tire au sort l'un des Pokémon de
data/wild/good_rod.asm, quelle que soit la carte. La Méga Canne lit la table de la carte dans
data/wild/super_rod.asm : Rouge et Bleu y tirent au sort un Pokémon d'un groupe, Jaune choisit l'un des quatre
emplacements de la carte selon les seuils de GenerateRandomFishingEncounter (engine/items/super_rod.asm). Une carte
absente de cette table ne donne rien à la Méga Canne.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .pret_source import macro_args, parse_int, source_lines

_ITEM_EFFECTS = "engine/items/item_effects.asm"
_GOOD_ROD = "data/wild/good_rod.asm"
_SUPER_ROD = "data/wild/super_rod.asm"
_YELLOW_SUPER_ROD_ENGINE = "engine/items/super_rod.asm"
_RANDOM_RANGE = 256
_YELLOW_SLOTS = 4


@dataclass(frozen=True)
class FishingSlot:
    species: str  # constante pret
    level: int
    chance: int  # en %, arrondi comme PokéAPI (total de 100 par table)


@dataclass(frozen=True)
class Gen1Fishing:
    old_rod: tuple[FishingSlot, ...]
    good_rod: tuple[FishingSlot, ...]
    super_rod: dict[str, tuple[FishingSlot, ...]]  # constante de carte -> emplacements


def read_fishing(root: Path) -> Gen1Fishing:
    return Gen1Fishing(_old_rod(root), _good_rod(root), _super_rod(root))


def _old_rod(root: Path) -> tuple[FishingSlot, ...]:
    lines = source_lines(root / _ITEM_EFFECTS)
    start = lines.index("ItemUseOldRod:")
    for line in lines[start : start + 4]:
        if match := re.fullmatch(r"lb bc, (\w+), (\w+)", line):
            return (FishingSlot(match.group(2), parse_int(match.group(1)), 100),)
    raise ValueError(f"{_ITEM_EFFECTS} : Pokémon de la Canne introuvable")


def _good_rod(root: Path) -> tuple[FishingSlot, ...]:
    pairs = [macro_args(line, "db") for line in source_lines(root / _GOOD_ROD) if line.startswith("db ")]
    return _equal_slots([(species, parse_int(level)) for level, species in pairs], _GOOD_ROD)


def _equal_slots(pairs: list[tuple[str, int]], where: str) -> tuple[FishingSlot, ...]:
    """Pokémon tirés au sort à parts égales."""
    if not pairs:
        raise ValueError(f"{where} : aucun Pokémon")
    chances = _percentages([1] * len(pairs))
    return tuple(FishingSlot(species, level, chance) for (species, level), chance in zip(pairs, chances, strict=True))


def _percentages(weights: list[int]) -> list[int]:
    """Pourcentages entiers de total 100 (méthode du plus fort reste, le premier emplacement d'abord)."""
    total = sum(weights)
    exact = [weight * 100 / total for weight in weights]
    result = [int(value) for value in exact]
    by_remainder = sorted(range(len(weights)), key=lambda index: result[index] - exact[index])
    for index in by_remainder[: 100 - sum(result)]:
        result[index] += 1
    return result


def _super_rod(root: Path) -> dict[str, tuple[FishingSlot, ...]]:
    lines = source_lines(root / _SUPER_ROD)
    if "SuperRodFishingSlots::" in lines:
        return _yellow_super_rod(root, lines)
    return _red_blue_super_rod(lines)


def _red_blue_super_rod(lines: list[str]) -> dict[str, tuple[FishingSlot, ...]]:
    """« dbw CARTE, .GroupN » puis chaque groupe : « db nombre » et « db niveau, Pokémon »."""
    group_of = {args[0]: args[1] for args in (macro_args(line, "dbw") for line in lines if line.startswith("dbw "))}
    groups: dict[str, list[tuple[str, int]]] = {}
    current: list[tuple[str, int]] | None = None
    for line in lines:
        if line.startswith(".Group") and line.endswith(":"):
            current = groups.setdefault(line[:-1], [])
        elif current is not None and line.startswith("db "):
            args = macro_args(line, "db")
            if len(args) == 2:
                current.append((args[1], parse_int(args[0])))
    unknown = set(group_of.values()) - groups.keys()
    if not group_of or unknown:
        raise ValueError(f"{_SUPER_ROD} : groupes de pêche absents ou inconnus : {sorted(unknown)}")
    return {const: _equal_slots(groups[group], f"{_SUPER_ROD} {group}") for const, group in group_of.items()}


def _yellow_super_rod(root: Path, lines: list[str]) -> dict[str, tuple[FishingSlot, ...]]:
    """« db CARTE, Pokémon, niveau » × 4 ; l'emplacement est choisi par les seuils de l'algorithme."""
    chances = _yellow_slot_chances(root)
    result = {}
    for line in lines:
        if not line.startswith("db ") or line == "db -1":
            continue
        args = macro_args(line, "db")
        if len(args) != 1 + 2 * _YELLOW_SLOTS:
            raise ValueError(f"{_SUPER_ROD} : ligne inattendue : {line}")
        result[args[0]] = tuple(
            FishingSlot(args[1 + 2 * slot], parse_int(args[2 + 2 * slot]), chances[slot])
            for slot in range(_YELLOW_SLOTS)
        )
    return result


def _yellow_slot_chances(root: Path) -> list[int]:
    """Probabilités des quatre emplacements : seuils croissants « cp $xx » de GenerateRandomFishingEncounter sur un
    tirage de 0 à 255."""
    lines = source_lines(root / _YELLOW_SUPER_ROD_ENGINE)
    start = lines.index("GenerateRandomFishingEncounter:")
    thresholds = [parse_int(line.removeprefix("cp ")) for line in lines[start:] if line.startswith("cp $")]
    if len(thresholds) != _YELLOW_SLOTS - 1 or thresholds != sorted(thresholds):
        raise ValueError(f"{_YELLOW_SUPER_ROD_ENGINE} : seuils de pêche inattendus : {thresholds}")
    bounds = [0, *thresholds, _RANDOM_RANGE]
    return _percentages([high - low for low, high in pairwise(bounds)])
