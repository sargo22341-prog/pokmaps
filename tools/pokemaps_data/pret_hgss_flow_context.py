"""Constantes et écritures des commandes HGSS, lus dans le moteur épinglé."""

import operator
import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_source import read_text


@dataclass(frozen=True)
class FlowContext:
    constants: dict[str, int]
    writes: dict[str, frozenset[int]]
    macros: dict[str, tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]]


def flow_context(root: Path) -> FlowContext:
    constants = read_constants(root)
    text = read_text(root / "asm/macros/script.inc")
    macros, opcodes = {}, {}
    for match in re.finditer(r"^\s*\.macro\s+(\w+)([^\n]*)\n(.*?)^\s*\.endm", text, re.M | re.S):
        name, parameters, body = match.groups()
        code = re.match(r"\s*\.short\s+(\d+)\b", body)
        if code:
            opcodes[name] = int(code[1])
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if lines and all(not line.startswith(".") for line in lines):
            params = tuple(p.strip() for p in parameters.split("//")[0].split(",") if p.strip())
            calls = tuple(
                (line.split()[0], tuple(a.strip() for a in line.partition(" ")[2].split(","))) for line in lines
            )
            macros[name] = params, calls
    functions = _function_writes(root)
    table = (
        read_text(root / "src/data/fieldmap/script_cmd_table.h").split("gScriptCmdTable[] = {", 1)[1].split("};", 1)[0]
    )
    names = re.findall(r"^\s+(\w+),", table, re.M)
    writes = {name: functions.get(names[opcode], frozenset(range(8))) for name, opcode in opcodes.items()}
    return FlowContext(constants, writes, macros)


def read_constants(root: Path) -> dict[str, int]:
    filenames = (
        "vars",
        "flags",
        "trainers",
        "species",
        "moves",
        "items",
        "std_script",
        "sprites",
        "trainer_class",
        "phone_contacts",
        "move_tutors",
        "maps",
        "apricorns",
        "badge",
        "scrcmd",
        "ribbon",
        "seals",
    )
    result = dict(TRUE=1, FALSE=0, eq=1, ne=5, lt=0, gt=2, le=3, ge=4)
    pending = {}
    for name in filenames:
        path = root / f"include/constants/{name}.h"
        if path.is_file():
            for key, value in re.findall(r"^#define[ \t]+(\w+)[ \t]+([^\n]+)", read_text(path), re.M):
                pending[key] = value.split("//")[0].strip()
    for _ in range(16):
        for key, value in tuple(pending.items()):
            parsed = _constant(value, result)
            if parsed is not None:
                result[key] = parsed
                del pending[key]
    config = read_text(root / "include/config.h")
    result.update(
        {name: int(value) for name, value in re.findall(r"#define (VERSION_(?:HEARTGOLD|SOULSILVER))\s+(\d+)", config)}
    )
    return result


def _constant(text: str, known: dict[str, int]) -> int | None:
    expression = text.strip().strip("()")
    if expression in known:
        return known[expression]
    try:
        return int(expression, 0)
    except ValueError:
        pass
    match = re.fullmatch(r"\(?([\w]+)\)?\s*(\+|-|<<|\|)\s*\(?([\w]+)\)?", expression)
    if not match:
        return None
    values = []
    for name in (match[1], match[3]):
        if name in known:
            values.append(known[name])
        elif re.fullmatch(r"0x[\da-fA-F]+|\d+", name):
            values.append(int(name, 0))
        else:
            return None
    return {"+": operator.add, "-": operator.sub, "<<": operator.lshift, "|": operator.or_}[match[2]](*values)


def _function_writes(root: Path) -> dict[str, frozenset[int]]:
    result = {}
    paths = sorted((root / "src").rglob("scrcmd*.c"))
    if len(paths) > 128:
        raise ValueError("HGSS : trop de fichiers de commandes")
    for path in paths:
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", read_text(path), flags=re.S)
        for name, body in re.findall(r"BOOL (ScrCmd_\w+)\(ScriptContext \*\w+\)\s*\{(.*?)^\}", text, re.M | re.S):
            reads = list(re.finditer(r"(?:(\w+)\s*=\s*)?(ScriptRead\w+|ScriptGetVar(?:Pointer)?)\(ctx\)", body))
            positions = {i for i, read in enumerate(reads) if read[2] == "ScriptGetVarPointer"}
            positions |= {
                i
                for i, read in enumerate(reads)
                if read[1] and re.search(r"GetVarPointer\([^;]+,\s*" + re.escape(read[1]) + r"\)", body)
            }
            result[name.removeprefix("ScrCmd_")] = frozenset(positions)
            result[name] = frozenset(positions)
    return result
