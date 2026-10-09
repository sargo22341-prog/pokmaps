"""Lecture bornée des sources JSON, C et assembleur GBA."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_CONDITIONAL_DEPTH = 32
_SYMBOLS = frozenset(
    {
        "RUBY",
        "SAPPHIRE",
        "EMERALD",
        "FIRERED",
        "LEAFGREEN",
        "ENGLISH",
        "GERMAN",
        "REVISION",
        "DEBUG_FIX",
        "DEBUG",
        "BUGFIX",
        "UBFIX",
        "MODERN",
    }
)


def read_text(path: Path) -> str:
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"{path} : source trop volumineuse")
    return path.read_text("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON : clé répétée {key}")
        result[key] = value
    return result


def _invalid_json_constant(value: str) -> None:
    raise ValueError(f"JSON : constante non finie interdite : {value}")


def read_json(path: Path) -> dict[str, Any]:
    try:
        result = json.loads(read_text(path), object_pairs_hook=_unique_object, parse_constant=_invalid_json_constant)
    except (ValueError, RecursionError) as error:
        raise ValueError(f"{path} : {error}") from error
    if not isinstance(result, dict):
        raise ValueError(f"{path} : objet JSON attendu")
    return result


def source_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{root} : chemin hors du dépôt : {relative}")
    return path


@dataclass
class _Branch:
    parent: bool
    active: bool
    taken: bool
    has_else: bool = False


def _atom(expression: str, defined: frozenset[str], path: Path) -> bool:
    expression = re.sub(
        r"defined\s*(?:\((\w+)\)|(\w+))",
        lambda match: str(int(_is_defined(match[1] or match[2], defined, path))),
        expression,
    ).strip()
    if expression in {"0", "1", "!0", "!1"}:
        return expression in {"1", "!0"}
    match = re.fullmatch(r"(!?)(\w+)(?:\s*(==|!=|>=|<=|>|<)\s*(\d+))?", expression)
    if not match or match[2] not in _SYMBOLS:
        raise ValueError(f"{path} : condition inconnue : {expression}")
    value = int(match[2] in defined)
    if match[3]:
        other = int(match[4])
        return {
            "==": value == other,
            "!=": value != other,
            ">=": value >= other,
            "<=": value <= other,
            ">": value > other,
            "<": value < other,
        }[match[3]]
    return bool(value) != bool(match[1])


def _is_defined(symbol: str, defined: frozenset[str], path: Path) -> bool:
    if symbol not in _SYMBOLS:
        raise ValueError(f"{path} : symbole conditionnel inconnu : {symbol}")
    return symbol in defined or symbol in {"REVISION", "DEBUG", "DEBUG_FIX"}


def _condition(expression: str, defined: frozenset[str], path: Path) -> bool:
    clauses = expression.split("||")
    if len(clauses) > 32:
        raise ValueError(f"{path} : condition trop longue")
    values = []
    for clause in clauses:
        atoms = clause.split("&&")
        if len(atoms) > 32:
            raise ValueError(f"{path} : condition trop longue")
        values.append(all([_atom(atom.strip(), defined, path) for atom in atoms]))
    return any(values)


def conditional_text(path: Path, defined: frozenset[str]) -> str:
    text = re.sub(r"/\*.*?\*/", "", read_text(path), flags=re.S)
    stack: list[_Branch] = []
    result: list[str] = []
    for raw in text.splitlines():
        line = raw.split("//", 1)[0].split("@", 1)[0].strip()
        directive = re.match(r"^(?:#|\.)(ifn?def|if|elif|else|endif)\b\s*(.*)", line)
        if directive:
            _directive(stack, directive[1], directive[2], defined, path)
        elif re.match(r"^(?:#|\.)(?:if|elif|else|endif)", line):
            raise ValueError(f"{path} : directive conditionnelle inconnue : {line}")
        elif not stack or stack[-1].active:
            result.append(line)
    if stack:
        raise ValueError(f"{path} : condition non terminée")
    return "\n".join(result)


def _directive(stack: list[_Branch], command: str, expression: str, defined: frozenset[str], path: Path) -> None:
    if command in {"if", "ifdef", "ifndef"}:
        if len(stack) >= MAX_CONDITIONAL_DEPTH:
            raise ValueError(f"{path} : conditions trop imbriquées")
        if command in {"ifdef", "ifndef"}:
            condition = _is_defined(expression, defined, path) != (command == "ifndef")
        else:
            condition = _condition(expression, defined, path)
        parent = not stack or stack[-1].active
        stack.append(_Branch(parent, parent and condition, condition))
        return
    if command in {"else", "endif"} and expression:
        raise ValueError(f"{path} : arguments inattendus après {command}")
    if not stack:
        raise ValueError(f"{path} : {command} sans condition")
    branch = stack[-1]
    if command == "endif":
        stack.pop()
    elif command == "else":
        if branch.has_else:
            raise ValueError(f"{path} : else répété")
        branch.active = branch.parent and not branch.taken
        branch.taken = branch.has_else = True
    elif command == "elif":
        if branch.has_else:
            raise ValueError(f"{path} : elif après else")
        condition = _condition(expression, defined, path)
        branch.active = branch.parent and not branch.taken and condition
        branch.taken |= condition


def read_initializers(path: Path, prefix: str, defined: frozenset[str] = frozenset()) -> dict[str, dict[str, str]]:
    text = conditional_text(path, defined)
    entries = re.findall(r"\[(" + re.escape(prefix) + r"\w+)\]\s*=\s*\{([^{}]*)\}", text, re.S)
    if len(entries) > 4096:
        raise ValueError(f"{path} : trop d’initialiseurs")
    result: dict[str, dict[str, str]] = {}
    for key, body in entries:
        fields = initializer_fields(body, path, key)
        if key in result:
            raise ValueError(f"{path} : entrée répétée {key}")
        result[key] = fields
    expected = re.findall(r"\[(" + re.escape(prefix) + r"\w+)\]\s*=", text)
    if not result or len(expected) != len(result):
        raise ValueError(f"{path} : initialiseurs absents ou non pris en charge")
    return result


def initializer_fields(body: str, path: Path, key: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    value_pattern = r"-?(?:0x[0-9a-fA-F]+|\d+|[A-Za-z_]\w*)(?:\s*[|&]\s*[A-Za-z_]\w*)*"
    for part in body.split(","):
        if not part.strip():
            continue
        match = re.fullmatch(r"\s*\.(\w+)\s*=\s*(" + value_pattern + r")\s*", part)
        if not match or match[1] in fields:
            raise ValueError(f"{path} : initialiseur invalide pour {key} : {part}")
        fields[match[1]] = match[2].strip()
    return fields
