"""Outils de lecture des fichiers assembleur RGBDS des désassemblages pret."""

from __future__ import annotations

import re
from pathlib import Path

_IF_DEF = re.compile(r"^IF\s+(!?)DEF\((\w+)\)$")


def strip_comment(line: str) -> str:
    """Retire le commentaire `; ...` d'une ligne (hors chaînes de caractères)."""
    in_string = False
    for i, char in enumerate(line):
        if char == '"':
            in_string = not in_string
        elif char == ";" and not in_string:
            return line[:i]
    return line


def preprocess(text: str, defines: set[str]) -> list[str]:
    """Évalue les blocs `IF DEF(X)` / `ELSE` / `ENDC`, retire les commentaires,
    ignore le contenu des `MACRO ... ENDM` et renvoie les lignes non vides."""
    lines: list[str] = []
    # Pile de booléens : chaque niveau indique si la branche courante est active.
    stack: list[bool] = []
    in_macro = False
    for raw in text.splitlines():
        line = strip_comment(raw).strip()
        if not line:
            continue
        if in_macro:
            if line == "ENDM":
                in_macro = False
            continue
        if line.startswith("MACRO "):
            in_macro = True
            continue
        match = _IF_DEF.match(line)
        if match:
            negate, name = match.groups()
            stack.append((name in defines) != bool(negate))
            continue
        if line.startswith("IF "):
            raise ValueError(f"Condition non gérée : {line!r}")
        if line == "ELSE":
            stack[-1] = not stack[-1]
            continue
        if line == "ENDC":
            stack.pop()
            continue
        if all(stack):
            lines.append(line)
    if stack:
        raise ValueError("Bloc IF non fermé")
    return lines


def read_lines(path: Path, defines: set[str]) -> list[str]:
    return preprocess(path.read_text(encoding="utf-8"), defines)


def split_args(text: str) -> list[str]:
    """Découpe les arguments d'une directive (`db 3, PIDGEY` -> ["3", "PIDGEY"])."""
    return [arg.strip() for arg in text.split(",") if arg.strip()]


def directive(line: str) -> tuple[str, list[str]]:
    """Renvoie (directive, arguments) pour une ligne comme `db 3, PIDGEY`."""
    head, _, rest = line.partition(" ")
    return head, split_args(rest)


def parse_number(token: str) -> int:
    """Lit un nombre RGBDS : décimal, `$hex` ou `%binaire`."""
    token = token.strip()
    if token.startswith("$"):
        return int(token[1:], 16)
    if token.startswith("%"):
        return int(token[1:], 2)
    return int(token)


def parse_constants(path: Path, directives: tuple[str, ...] = ("const",)) -> dict[str, int]:
    """Lit une liste de constantes `const_def` / `const` / `const_skip` / `const_next`.

    `directives` liste les macros qui déclarent une constante (ex. `map_const`)."""
    values: dict[str, int] = {}
    current = 0
    for line in read_lines(path, set()):
        name, args = directive(line)
        if name == "const_def":
            current = parse_number(args[0]) if args else 0
        elif name == "const_skip":
            current += parse_number(args[0]) if args else 1
        elif name == "const_next":
            current = parse_number(args[0])
        elif name in directives:
            values[args[0]] = current
            current += 1
    return values


def labelled_blocks(lines: list[str]) -> dict[str, list[str]]:
    """Regroupe les lignes sous leur étiquette (`Label:` ou `Label::`).
    Les étiquettes locales (`.Group1:`) sont préfixées par l'étiquette parente."""
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    parent: str | None = None
    for line in lines:
        if line.endswith(":") and " " not in line:
            label = line.rstrip(":")
            if label.startswith("."):
                current = f"{parent}{label}"
            else:
                parent = current = label
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return blocks
