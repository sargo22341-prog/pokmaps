"""Fonctions partagées pour lire les sources texte des désassemblages pret."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

COMMENT = re.compile(r";.*$")
_IF_DEF = re.compile(r"^(?:IF|ELIF) DEF\((\w+)\)$", re.IGNORECASE)


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


@dataclass
class _Branch:
    """Bloc IF en cours : sa branche courante est-elle assemblée, et une branche précédente l'a-t-elle été ?"""

    active: bool
    taken: bool


def conditional_lines(path: Path, defined: frozenset[str]) -> list[str]:
    """Lignes d'un fichier dont les blocs IF DEF(…) / ELIF DEF(…) / ELSE / ENDC sont résolus pour les symboles
    `defined` ; une autre forme de condition arrête la lecture.

    pret assemble plusieurs versions depuis les mêmes sources : IF DEF(_RED) garde ce qui est propre à Rouge,
    IF DEF(_GOLD) … ELIF DEF(_SILVER) choisit entre Or et Argent. Les mots-clés s'écrivent aussi en minuscules."""
    return [code for code, _ in conditional_annotated_lines(path, defined)]


def conditional_annotated_lines(path: Path, defined: frozenset[str]) -> list[tuple[str, str]]:
    """Comme `conditional_lines`, chaque ligne avec son commentaire de fin de ligne (`annotated_lines`)."""
    result: list[tuple[str, str]] = []
    stack: list[_Branch] = []
    for line, comment in annotated_lines(path):
        keyword = line.split(maxsplit=1)[0].upper()
        if keyword in ("IF", "ELIF"):
            match = _IF_DEF.match(line)
            if match is None:
                raise ValueError(f"{path.name} : condition non prise en charge : {line}")
            _open_branch(stack, keyword, match.group(1) in defined, path)
        elif keyword in ("ELSE", "ENDC"):
            if not stack:
                raise ValueError(f"{path.name} : {line} sans IF")
            if keyword == "ELSE":
                stack[-1] = _Branch(not stack[-1].taken, True)
            else:
                stack.pop()
        elif all(branch.active for branch in stack):
            result.append((line, comment))
    if stack:
        raise ValueError(f"{path.name} : bloc IF non terminé")
    return result


def _open_branch(stack: list[_Branch], keyword: str, condition: bool, path: Path) -> None:
    if keyword == "IF":
        stack.append(_Branch(condition, condition))
        return
    if not stack:
        raise ValueError(f"{path.name} : ELIF sans IF")
    active = condition and not stack[-1].taken
    stack[-1] = _Branch(active, stack[-1].taken or active)


def macro_args(line: str, macro: str) -> list[str]:
    return [arg.strip() for arg in line[len(macro) :].split(",")]


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value)
