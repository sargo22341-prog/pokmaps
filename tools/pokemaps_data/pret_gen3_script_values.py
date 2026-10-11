"""Valeurs numériques explicites des scripts, sans exécuter d'expression de source."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .pret_gen3_source import read_text


def script_constants(root: Path) -> dict[str, int]:
    expressions: dict[str, str] = {"TRUE": "1", "FALSE": "0", "YES": "1", "NO": "0"}
    values: dict[str, int] = {}
    for path in sorted((root / "include/constants").glob("*.h")):
        text = re.sub(r"/\*.*?\*/", "", read_text(path), flags=re.S)
        text = re.sub(r"//[^\n]*", "", text)
        if path.name == "items.h":
            values.update(_item_enums(text))
        for name, expression in re.findall(r"^#define[ \t]+(\w+)[ \t]+([^\n]+)", text, re.M):
            expression = expression.split("//", 1)[0].strip()
            if re.fullmatch(r"[\w\s()+\-<>]+", expression):
                expressions[name] = expression
    for _ in range(32):
        added = {
            name: number for name, expr in expressions.items() if (number := number_value(expr, values)) is not None
        }
        if added.keys() <= values.keys():
            return values | _machine_aliases(root, values)
        values.update(added)
    raise ValueError(f"{root} : constantes de scripts trop profondément dépendantes")


def _machine_aliases(root: Path, values: dict[str, int]) -> dict[str, int]:
    path = root / "include/constants/tms_hms.h"
    if not path.is_file():
        return {}
    text = read_text(path)
    aliases = {}
    for kind, count in (("TM", 50), ("HM", 8)):
        match = re.search(r"#define FOREACH_" + kind + r"\(F\)(.*?)(?=\n\s*#|$)", text, re.S)
        moves = re.findall(r"F\((\w+)\)", match[1]) if match else []
        if len(moves) != count or len(set(moves)) != count:
            raise ValueError(f"{path} : liste de {kind} absente ou invalide")
        for index, move in enumerate(moves, 1):
            numbered = f"ITEM_{kind}{index:02}"
            if numbered not in values:
                raise ValueError(f"{path} : constante de machine absente : {numbered}")
            aliases[f"ITEM_{kind}_{move}"] = values[numbered]
    return aliases


def _item_enums(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for body in re.findall(r"enum\s*\{([^{}]+)\}", text, re.S):
        number = 0
        for entry in body.split(","):
            entry = entry.strip()
            if not entry:
                continue
            match = re.fullmatch(r"(\w+)(?:\s*=\s*(.*))?", entry)
            if not match:
                raise ValueError(f"Constante d'objet illisible : {entry}")
            if match[2]:
                explicit = number_value(match[2], values)
                if explicit is None:
                    raise ValueError(f"Constante d'objet non résolue : {entry}")
                number = explicit
            values[match[1]] = number
            number += 1
    return values


def number_value(expression: str, constants: dict[str, int]) -> int | None:
    """Sommes et différences des constantes pret ; une expression étrangère reste non résolue."""
    if len(expression) > 1024 or expression.count("(") > 32:
        return None
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError:
        return None
    return _number_expression(tree.body, constants, 0)


def _number_expression(node: ast.expr, constants: dict[str, int], depth: int) -> int | None:
    # La profondeur de l'expression borne explicitement cette récursion de lecture.
    if depth > 32:
        return None
    match node:
        case ast.Constant(value=value):
            return value if type(value) is int else None
        case ast.Name(id=name):
            return constants.get(name)
        case ast.UnaryOp(op=operator, operand=operand) if isinstance(operator, (ast.UAdd, ast.USub)):
            value = _number_expression(operand, constants, depth + 1)
            return None if value is None else -value if isinstance(operator, ast.USub) else value
        case ast.BinOp(left=left, op=operator, right=right) if isinstance(operator, (ast.Add, ast.Sub)):
            a = _number_expression(left, constants, depth + 1)
            b = _number_expression(right, constants, depth + 1)
            if a is None or b is None:
                return None
            return a + b if isinstance(operator, ast.Add) else a - b
        case ast.BinOp(left=left, op=ast.LShift(), right=right):
            a = _number_expression(left, constants, depth + 1)
            b = _number_expression(right, constants, depth + 1)
            if a is None or b is None or not 0 <= a <= 65535 or not 0 <= b <= 15:
                return None
            return a << b
        case _:
            return None


def range_values(value: str) -> range | None:
    if not value.startswith("range:"):
        return None
    _, first, end = value.split(":")
    return range(int(first), int(end))


def shifted_value(value: str, offset: int, constants: dict[str, int]) -> str:
    if values := range_values(value):
        return f"range:{values.start + offset}:{values.stop + offset}"
    number = number_value(value, constants)
    return str(number + offset) if number is not None else value
