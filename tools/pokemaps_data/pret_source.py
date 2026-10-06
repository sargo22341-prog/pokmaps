"""Fonctions partagees pour lire les sources texte des desassemblages pret."""

from __future__ import annotations

import re
from pathlib import Path

COMMENT = re.compile(r";.*$")


def source_lines(path: Path) -> list[str]:
    """Lignes d'un fichier sans commentaires ni espaces superflus."""
    return [line for line in (COMMENT.sub("", raw).strip() for raw in path.read_text("utf-8").splitlines()) if line]


def macro_args(line: str, macro: str) -> list[str]:
    return [arg.strip() for arg in line[len(macro) :].split(",")]


def parse_int(value: str) -> int:
    value = value.strip()
    if value.startswith("$"):
        return int(value[1:], 16)
    return int(value)
