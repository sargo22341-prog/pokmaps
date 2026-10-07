"""Fonctions partagees pour lire les sources texte des desassemblages pret."""

from __future__ import annotations

import re
from pathlib import Path

COMMENT = re.compile(r";.*$")
_IF_DEF = re.compile(r"^IF DEF\((\w+)\)$")


def source_lines(path: Path) -> list[str]:
    """Lignes d'un fichier sans commentaires ni espaces superflus."""
    return [line for line in (COMMENT.sub("", raw).strip() for raw in path.read_text("utf-8").splitlines()) if line]


def annotated_lines(path: Path) -> list[tuple[str, str]]:
    """Lignes de code d'un fichier, chacune avec son commentaire de fin de ligne (sans le « ; »)."""
    result = []
    for raw in path.read_text("utf-8").splitlines():
        code, _, comment = raw.partition(";")
        if code.strip():
            result.append((code.strip(), comment.strip()))
    return result


def conditional_lines(path: Path, defined: frozenset[str]) -> list[str]:
    """Lignes d'un fichier dont les blocs IF DEF(…) / ELSE / ENDC sont résolus pour les symboles `defined`.

    pokered assemble Rouge et Bleu depuis les mêmes sources : IF DEF(_RED) garde ce qui est propre à Rouge."""
    result: list[str] = []
    active: list[bool] = []
    for line in source_lines(path):
        if match := _IF_DEF.match(line):
            active.append(match.group(1) in defined)
        elif line.startswith("IF "):
            raise ValueError(f"{path.name} : condition non prise en charge : {line}")
        elif line in ("ELSE", "ENDC"):
            if not active:
                raise ValueError(f"{path.name} : {line} sans IF")
            if line == "ELSE":
                active[-1] = not active[-1]
            else:
                active.pop()
        elif all(active):
            result.append(line)
    if active:
        raise ValueError(f"{path.name} : bloc IF non terminé")
    return result


def macro_args(line: str, macro: str) -> list[str]:
    return [arg.strip() for arg in line[len(macro) :].split(",")]


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value)
