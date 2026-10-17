"""Fichier et point d'entrée de chaque numéro de script DS, tranche par tranche, comme les choisit le moteur.

Un événement, une commande CallCommonScript ou une table d'initialisation désigne un script par un numéro. Le
moteur compare ce numéro aux débuts de tranche, du plus grand au plus petit : au-delà d'un début, il charge le
fichier de la tranche et retranche ce début ; de 1 à 1999, il garde le fichier du lieu et retranche 1. Platine
écrit ces tranches dans SCRIPT_RANGE_TABLE (src/script_manager.c, débuts dans include/script_manager.h).
Diamant/Perle les écrit en assembleur (LoadScriptsAndMessagesByMapId) : la fonction est rejouée instruction par
instruction, et chaque tranche doit retrancher exactement son début.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_engine_text import asm_function
from .pret_gen4_source import c_defines, read_text

_DP_FILE = "arm9/asm/unk_02038C78.s"
_DP_LOADER = "LoadScriptsAndMessagesByMapId"
_DP_LOAD = "bl LoadScriptsAndMessagesParameterized"
_DP_LOCAL = "bl LoadScriptsAndMessagesForCurrentMap"
_DP_END = "b _0203920A"
_LOCAL_START = 1
# Une tranche par fichier commun : Platine en compte une trentaine.
_MAX_RANGES = 64
_REGISTER = r"(r[0-7])"
_IMMEDIATE = r"#(0x[0-9a-fA-F]+|\d+)"


@dataclass(frozen=True)
class ScriptRange:
    start: int
    file: int  # numéro du fichier de scripts (celui des en-têtes de lieux)


@dataclass(frozen=True)
class ScriptRanges:
    ranges: tuple[ScriptRange, ...]  # du plus grand début au plus petit

    def locate(self, script: int) -> tuple[int, int] | None:
        """(fichier, rang du point d'entrée) d'un numéro de script commun ; None pour un script du lieu (1 à 1999,
        rang `script - 1` dans le fichier du lieu) ou pour 0, qui ne désigne aucun script."""
        for found in self.ranges:
            if script >= found.start:
                return found.file, script - found.start
        return None


def read_script_ranges(root: Path, scripts_order: dict[str, int] | None) -> ScriptRanges:
    if scripts_order is not None:
        return _platinum(root, scripts_order)
    return _diamond_pearl(root)


def _platinum(root: Path, scripts_order: dict[str, int]) -> ScriptRanges:
    offsets = c_defines(root / "include/script_manager.h", "SCRIPT_ID_OFFSET_")
    manager = read_text(root / "src/script_manager.c")
    table = re.search(r"#define SCRIPT_RANGE_TABLE\(Entry\)(.*?)// clang-format on", manager, re.DOTALL)
    if table is None or "else if (retScriptID >= 1)" not in manager or "retScriptID -= threshold;" not in manager:
        raise ValueError(f"{root} : SCRIPT_RANGE_TABLE ou ScriptContext_LoadAndOffsetID modifiés")
    entries = re.findall(r"Entry\((SCRIPT_ID_OFFSET_\w+),\s*(\w+),", table.group(1))
    ranges = []
    for offset, name in entries:
        if offset not in offsets or name not in scripts_order:
            raise ValueError(f"{root} : tranche de scripts inconnue : {offset}, {name}")
        ranges.append(ScriptRange(offsets[offset], scripts_order[name]))
    return _checked(tuple(ranges), str(root))


def _diamond_pearl(root: Path) -> ScriptRanges:
    lines = asm_function(read_text(root / _DP_FILE), _DP_LOADER, _DP_FILE)
    words = (re.fullmatch(r"(_\w+): \.word (0x[0-9a-fA-F]+)", line) for line in lines)
    pool = {match.group(1): int(match.group(2), 0) for match in words if match}
    registers: dict[str, int] = {}
    saved: dict[str, int] | None = None
    threshold: int | None = None
    ranges: list[ScriptRange] = []
    file: int | None = None
    local = False
    for line in lines:
        if line == _DP_END and saved is not None:
            if threshold is None or (file is None and not local):
                raise ValueError(f"{root / _DP_FILE} : tranche sans début ni fichier")
            if not local and file is not None:
                ranges.append(ScriptRange(threshold, file))
            registers, saved, file, local = saved, None, None, False
        elif match := re.fullmatch(rf"cmp r4, (?:{_REGISTER}|{_IMMEDIATE})", line):
            threshold = registers[match.group(1)] if match.group(1) else int(match.group(2), 0)
        elif line.startswith("blo "):
            saved = dict(registers)
        elif line == _DP_LOAD:
            file = registers["r2"]
        elif line == _DP_LOCAL:
            local = threshold == _LOCAL_START
            if not local:
                raise ValueError(f"{root / _DP_FILE} : scripts du lieu hors de la tranche 1")
        elif match := re.fullmatch(rf"sub r0, r4, (?:{_REGISTER}|{_IMMEDIATE})", line):
            offset = registers[match.group(1)] if match.group(1) else int(match.group(2), 0)
            if offset != threshold:
                raise ValueError(f"{root / _DP_FILE} : tranche {threshold} retranche {offset}")
        else:
            _execute(line, registers, pool)
    return _checked(tuple(ranges), str(root / _DP_FILE))


def _execute(line: str, registers: dict[str, int], pool: dict[str, int]) -> None:
    """Instructions qui calculent les débuts de tranche et les fichiers ; r4 (le numéro demandé) reste inconnu."""
    if match := re.fullmatch(rf"ldr {_REGISTER}, (_\w+)", line):
        registers[match.group(1)] = pool[match.group(2)]
    elif match := re.fullmatch(rf"mov {_REGISTER}, {_IMMEDIATE}", line):
        registers[match.group(1)] = int(match.group(2), 0)
    elif match := re.fullmatch(rf"(add|sub) {_REGISTER}, (?:{_REGISTER}, )?{_IMMEDIATE}", line):
        operation, target, source, value = match.groups()
        base = registers.get(source or target)
        if base is not None:
            registers[target] = base + int(value, 0) if operation == "add" else base - int(value, 0)
    elif match := re.fullmatch(rf"(lsl|lsr) {_REGISTER}, {_REGISTER}, {_IMMEDIATE}", line):
        operation, target, source, value = match.groups()
        if source in registers:
            shift = int(value, 0)
            registers[target] = registers[source] << shift if operation == "lsl" else registers[source] >> shift


def _checked(ranges: tuple[ScriptRange, ...], where: str) -> ScriptRanges:
    starts = [found.start for found in ranges]
    if not 0 < len(ranges) <= _MAX_RANGES or starts != sorted(set(starts), reverse=True) or starts[-1] <= _LOCAL_START:
        raise ValueError(f"{where} : tranches de scripts illisibles : {starts}")
    return ScriptRanges(ranges)
