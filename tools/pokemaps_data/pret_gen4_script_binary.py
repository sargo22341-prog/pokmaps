"""Désassemblage des scripts compilés de Diamant/Perle (files/fielddata/script/scr_seq_release).

Un fichier de scripts commence par la table des points d'entrée (mots relatifs, terminée par 0xFD13), comme
l'écrivent les macros ScriptEntry de Platine ; les commandes suivent, chacune un opcode u16 et ses arguments
(pret_gen4_script_commands). Le désassemblage suit le flux depuis chaque entrée : sauts et appels ouvrent de
nouveaux chemins, End, Return et les sauts inconditionnels les ferment, et les adresses de données désignent des
listes de mouvements (action u16, nombre u16, jusqu'à l'action 0xFE). Un fichier d'initialisation (scripts
lancés à l'entrée dans un lieu) a sa propre forme : type u8, puis numéro de script ou table de conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .pret_gen4_script_commands import Argument, ScriptCommand
from .pret_gen4_source import ByteReader, read_binary

ENTRY_END = 0xFD13
MOVEMENT_END = 0xFE
_MAX_SCRIPT_BYTES = 64 * 1024
_FRAME_TABLE = 1
_FIXED_INIT_TYPES = frozenset({2, 3, 4})


@dataclass(frozen=True)
class Instruction:
    offset: int
    opcode: int
    name: str
    # Valeurs des arguments ; une adresse relative est convertie en décalage absolu dans le fichier.
    arguments: tuple[int, ...]
    size: int


@dataclass(frozen=True)
class ScriptFile:
    entries: tuple[int, ...]
    instructions: dict[int, Instruction]
    movements: dict[int, tuple[tuple[int, int], ...]]


@dataclass(frozen=True)
class InitScripts:
    """Scripts lancés à l'entrée dans un lieu : (type, numéro de script) et conditions (variable, valeur,
    numéro de script) vérifiées à chaque image."""

    fixed: tuple[tuple[int, int], ...]
    frame_table: tuple[tuple[int, int, int], ...]


def read_script_file(path: Path, commands: tuple[ScriptCommand, ...]) -> ScriptFile:
    reader = ByteReader(read_binary(path, _MAX_SCRIPT_BYTES), str(path))
    entries = _entries(reader)
    instructions: dict[int, Instruction] = {}
    movements: dict[int, tuple[tuple[int, int], ...]] = {}
    pending = list(entries)
    # Chaque décalage n'est décodé qu'une fois : le parcours est borné par la taille du fichier.
    while pending:
        offset = pending.pop()
        while offset not in instructions:
            instruction, targets, data, ends = _decode(reader, offset, commands)
            instructions[offset] = instruction
            pending.extend(targets)
            for target in data:
                movements.setdefault(target, _movement(reader, target))
            if ends:
                break
            offset += instruction.size
    _check_overlaps(instructions, movements, reader.where)
    return ScriptFile(tuple(entries), instructions, movements)


def _entries(reader: ByteReader) -> list[int]:
    """Points d'entrée jusqu'à 0xFD13, ou jusqu'au premier octet de code : quelques fichiers n'ont pas de
    marqueur, le moteur n'en ayant pas besoin pour trouver un script par son numéro."""
    entries: list[int] = []
    offset = 0
    while offset < min(entries, default=len(reader.data)) and reader.u16(offset) != ENTRY_END:
        target = offset + 4 + reader.s32(offset)
        reader.require(target, 2)
        entries.append(target)
        offset += 4
    if not entries:
        raise ValueError(f"{reader.where} : aucun point d'entrée")
    return entries


def _decode(
    reader: ByteReader, offset: int, commands: tuple[ScriptCommand, ...]
) -> tuple[Instruction, list[int], list[int], bool]:
    opcode = reader.u16(offset)
    if opcode >= len(commands):
        raise ValueError(f"{reader.where} : commande inconnue {opcode:#06x} à {offset:#x}")
    command = commands[opcode]
    if command.problem is not None:
        raise ValueError(f"{reader.where} : commande {command.name} illisible à {offset:#x} ({command.problem})")
    position = offset + 2
    values: list[int] = []
    targets: list[int] = []
    data: list[int] = []
    arguments = list(command.arguments)
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        value, position = _argument(reader, argument, position)
        if argument.role in {"jump", "call"}:
            targets.append(value)
        elif argument.role == "data":
            data.append(value)
        if index == 0 and command.cases:
            arguments.extend(dict(command.cases).get(value, ()))
        values.append(value)
        index += 1
    instruction = Instruction(offset, opcode, command.name, tuple(values), position - offset)
    return instruction, targets, data, command.ends


def _argument(reader: ByteReader, argument: Argument, position: int) -> tuple[int, int]:
    if argument.size == 1:
        value = reader.u8(position)
    elif argument.size == 2:
        value = reader.u16(position)
    else:
        value = reader.s32(position) if argument.role in {"jump", "call", "data"} else reader.u32(position)
    position += argument.size
    if argument.role in {"jump", "call", "data"}:
        value += position
        reader.require(value, 2)
    return value, position


def _movement(reader: ByteReader, offset: int) -> tuple[tuple[int, int], ...]:
    steps = []
    for position in range(offset, len(reader.data) - 3, 4):
        action, count = reader.unpack("HH", position)
        if action == MOVEMENT_END:
            return tuple(steps)
        steps.append((action, count))
    raise ValueError(f"{reader.where} : mouvements sans fin à {offset:#x}")


def _check_overlaps(
    instructions: dict[int, Instruction], movements: dict[int, tuple[tuple[int, int], ...]], where: str
) -> None:
    spans = sorted(
        [(i.offset, i.offset + i.size) for i in instructions.values()]
        + [(start, start + 4 * (len(steps) + 1)) for start, steps in movements.items()]
    )
    for (_, end), (start, _) in pairwise(spans):
        if start < end:
            raise ValueError(f"{where} : code et données se chevauchent à {start:#x}")


def read_init_scripts(path: Path) -> InitScripts:
    reader = ByteReader(read_binary(path, _MAX_SCRIPT_BYTES), str(path))
    fixed = []
    table: list[tuple[int, int, int]] = []
    offset = 0
    while kind := reader.u8(offset):
        if kind == _FRAME_TABLE:
            if table:
                raise ValueError(f"{path} : deux tables de conditions")
            table = _frame_table(reader, offset + 5 + reader.s32(offset + 1))
            offset += 5
        elif kind in _FIXED_INIT_TYPES:
            script, zero = reader.unpack("HH", offset + 1)
            if zero:
                raise ValueError(f"{path} : entrée d'initialisation inattendue à {offset:#x}")
            fixed.append((kind, script))
            offset += 5
        else:
            raise ValueError(f"{path} : type d'initialisation inconnu {kind} à {offset:#x}")
    return InitScripts(tuple(fixed), tuple(table))


def _frame_table(reader: ByteReader, offset: int) -> list[tuple[int, int, int]]:
    rows = []
    while reader.u16(offset):
        rows.append(reader.unpack("3H", offset))
        offset += 6
    return rows
