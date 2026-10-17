"""Revanches du Cherche VS : table des équipes par niveau et drapeaux qui débloquent chaque niveau.

Platine : gVsSeekerRematchData (src/overlay005/vs_seeker.c), SystemFlag_CheckUnlockedVsSeekerLevel
(src/system_flags.c). Diamant/Perle : ov05_021F691C, lue par les fonctions ov05_021E189C à ov05_021E1964
(arm9/overlays/05), et sub_0205EEB8 (arm9/src/unk_0205EC84.c).

Une ligne donne six numéros de dresseurs : l'équipe de base puis une par niveau 1 à 5. 0xFFFF laisse un niveau
sans équipe et 0 termine la ligne. Le moteur prend le premier niveau dont l'équipe n'a pas encore été battue
(VsSeeker_GetCurrentLevelForRematchData) ; si ce niveau n'est pas débloqué, il redescend au niveau le plus
proche qui a une équipe (VsSeeker_AdjustRematchLevel), jusqu'à l'équipe de base.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_engine_text import asm_data, asm_function, c_function, c_initializer
from .pret_gen4_source import metang_enum, read_text

LEVELS = 6
NO_TEAM = 0xFFFF
END = 0
_PLATINUM_TABLE = "src/overlay005/vs_seeker.c"
_PLATINUM_FLAGS = "src/system_flags.c"
_DP_OVERLAY = "arm9/overlays/05/asm/ov05_021E1374.s"
_DP_FLAGS = "arm9/src/unk_0205EC84.c"
_DP_TABLE = "ov05_021F691C"
_DP_ROWS = 0xF0
# Forme des fonctions de Diamant/Perle qui lisent la table : recherche de la ligne, niveau courant, niveau inférieur.
_DP_SHAPES = {
    "ov05_021E189C": ("ldr r3, _021E18B8", "add r3, #0xc", f"cmp r2, #{_DP_ROWS:#x}"),
    "ov05_021E18BC": (
        "mov r0, #0xc",
        "ldr r7, _021E1904",
        "cmp r1, #0",
        "bl TrainerFieldSystem_FlagCheck",
        "cmp r4, #6",
    ),
    "ov05_021E1908": ("bl sub_0205EEB8", "bl ov05_021E1930"),
    "ov05_021E1930": ("mov r1, #0xc", "ldr r1, _021E1960"),
}


@dataclass(frozen=True)
class RematchSeries:
    """Équipes d'un dresseur : `teams[0]` est l'équipe de base, `teams[n]` celle du niveau n (None si aucune)."""

    teams: tuple[int | None, ...]

    @property
    def base(self) -> int:
        base = self.teams[0]
        if base is None:
            raise ValueError("série de revanches sans équipe de base")
        return base


@dataclass(frozen=True)
class VsSeekerRules:
    series: tuple[RematchSeries, ...]
    # Drapeau qui débloque chaque niveau, du niveau 1 au niveau 5.
    unlock_flags: tuple[int, ...]


def read_vs_seeker(root: Path, repo: str, trainers: dict[str, int] | None) -> VsSeekerRules:
    """Table du Cherche VS ; `trainers` donne les numéros des constantes de Platine (None pour Diamant/Perle)."""
    if repo == "pokeplatinum" and trainers is not None:
        rows, flags = _platinum_rows(root, trainers), _platinum_flags(root)
    elif repo == "pokediamond":
        rows, flags = _dp_rows(root), _dp_flags(root)
    else:
        raise ValueError(f"Dépôt du Cherche VS inconnu : {repo}")
    series = tuple(_series(row, f"{root} ligne {index}") for index, row in enumerate(rows))
    bases = [entry.base for entry in series]
    if len(set(bases)) != len(bases):
        raise ValueError(f"{root} : dresseur de base répété dans le Cherche VS")
    return VsSeekerRules(series, flags)


def _series(row: tuple[int, ...], where: str) -> RematchSeries:
    if len(row) != LEVELS or row[0] in {NO_TEAM, END}:
        raise ValueError(f"{where} : ligne du Cherche VS invalide : {row}")
    teams: list[int | None] = []
    for value in row:
        if value == END:
            break
        teams.append(None if value == NO_TEAM else value)
    if teams[-1] is None:
        raise ValueError(f"{where} : ligne du Cherche VS terminée par un niveau vide")
    return RematchSeries(tuple(teams))


def _platinum_rows(root: Path, trainers: dict[str, int]) -> list[tuple[int, ...]]:
    text = read_text(root / _PLATINUM_TABLE)
    expected = (
        "#define VS_SEEKER_MAX_REMATCHES     6",
        "#define VS_SEEKER_REMATCH_DATA_NONE 0xFFFF",
        "#define VS_SEEKER_REMATCH_DATA_END  0",
        "#define _ VS_SEEKER_REMATCH_DATA_NONE",
    )
    if any(line not in text for line in expected):
        raise ValueError(f"{root / _PLATINUM_TABLE} : constantes du Cherche VS modifiées")
    body = c_initializer(text, "gVsSeekerRematchData", _PLATINUM_TABLE)
    pattern = re.compile(r"NoUniqueRematches\((\w+)\)|\{([^{}]*)\}")
    if pattern.sub("", body).strip(" \t\r\n,"):
        raise ValueError(f"{root / _PLATINUM_TABLE} : ligne du Cherche VS illisible")
    words = {"_": NO_TEAM, "VS_SEEKER_REMATCH_DATA_END": END, **trainers}
    rows = []
    for match in pattern.finditer(body):
        single = match.group(1)
        names = [single] * 2 + ["VS_SEEKER_REMATCH_DATA_END"] * 4 if single else match.group(2).split(",")
        if unknown := [name.strip() for name in names if name.strip() not in words]:
            raise ValueError(f"{root / _PLATINUM_TABLE} : constantes inconnues : {unknown}")
        rows.append(tuple(words[name.strip()] for name in names))
    return rows


def _platinum_flags(root: Path) -> tuple[int, ...]:
    body = c_function(read_text(root / _PLATINUM_FLAGS), "SystemFlag_CheckUnlockedVsSeekerLevel", _PLATINUM_FLAGS)
    cases = re.findall(r"case\s+(\d+):\s*result\s*=\s*CheckFlag\(varsFlags,\s*(\w+)\);\s*break;", body)
    flags = metang_enum(root / "generated/vars_flags.txt")
    return _flag_table([(int(level), flags.get(name, -1)) for level, name in cases], _PLATINUM_FLAGS)


def _dp_rows(root: Path) -> list[tuple[int, ...]]:
    text = read_text(root / _DP_OVERLAY)
    for label, lines in _DP_SHAPES.items():
        body = asm_function(text, label, _DP_OVERLAY)
        if any(line not in body for line in lines):
            raise ValueError(f"{root / _DP_OVERLAY} : fonction {label} du Cherche VS modifiée")
    data = asm_data(text, _DP_TABLE, _DP_OVERLAY)
    size = 2 * LEVELS
    if len(data) != _DP_ROWS * size:
        raise ValueError(f"{root / _DP_OVERLAY} : {len(data)} octets pour la table du Cherche VS")
    return [
        tuple(int.from_bytes(data[row + 2 * level : row + 2 * level + 2], "little") for level in range(LEVELS))
        for row in range(0, len(data), size)
    ]


def _dp_flags(root: Path) -> tuple[int, ...]:
    body = c_function(read_text(root / _DP_FLAGS), "sub_0205EEB8", _DP_FLAGS)
    cases = re.findall(r"case\s+(\d+):\s*ret\s*=\s*_flag_check\(state,\s*(0x[0-9A-Fa-f]+)\);\s*break;", body)
    return _flag_table([(int(level), int(flag, 16)) for level, flag in cases], _DP_FLAGS)


def _flag_table(cases: list[tuple[int, int]], where: str) -> tuple[int, ...]:
    if [level for level, _ in cases] != list(range(1, LEVELS)) or any(flag < 0 for _, flag in cases):
        raise ValueError(f"{where} : drapeaux des niveaux du Cherche VS illisibles : {cases}")
    return tuple(flag for _, flag in cases)
