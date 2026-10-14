"""Variables de scripts que les appels C peuvent écrire, y compris via un sous-appel."""

from __future__ import annotations

import re
from pathlib import Path

from .pret_gen3_source import read_text

_FUNCTION = r"(?m)^(?:static\s+)?(?:\w+[ \t*]+)+(\w+)\([^;{}]*\)\s*\{"
_SPECIAL_VARS = {"Result": "VAR_RESULT", "ItemId": "VAR_ITEM_ID", "Facing": "VAR_FACING"}


def special_writes(root: Path) -> dict[str, frozenset[str]]:
    """L'union des versions et des fonctions homonymes reste prudente : une valeur oubliée devient inconnue."""
    files = sorted((root / "src").glob("*.c"))
    if len(files) > 1024:
        raise ValueError(f"{root} : trop de fichiers C à analyser")
    writes: dict[str, frozenset[str]] = {}
    calls: dict[str, frozenset[str]] = {}
    easy_chat_writes: set[str] = set()
    for path in files:
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", read_text(path), flags=re.S)
        text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
        for name, body in _function_regions(text, path):
            modified = re.findall(r"\bgSpecialVar_(\w+)\s*(?:[+*/&|^-]?=(?!=)|\+\+|--)", body)
            variables = {_SPECIAL_VARS.get(var, "VAR_" + var) for var in modified}
            variables.update(re.findall(r"\bVarSet\(\s*(VAR_\w+)\s*,", body))
            if path.name.startswith("easy_chat"):
                easy_chat_writes.update(variables)
            writes[name] = writes.get(name, frozenset()) | variables
            calls[name] = calls.get(name, frozenset()) | set(re.findall(r"\b(\w+)\s*\(", body))
    if "ShowEasyChatScreen" in writes:
        # Le dialogue rend la main via des callbacks : ses écritures dépassent l'appel C initial.
        writes["ShowEasyChatScreen"] |= easy_chat_writes
    for _ in range(32):
        expanded = {
            name: variables | frozenset(var for callee in calls[name] for var in writes.get(callee, ()))
            for name, variables in writes.items()
        }
        if expanded == writes:
            return writes
        writes = expanded
    raise ValueError(f"{root} : appels C trop profondément dépendants")


def _function_regions(text: str, path: Path) -> list[tuple[str, str]]:
    # Certaines branches de compilation doublent une accolade. L'étendue jusqu'à la fonction suivante
    # peut inclure des données, mais ne retire jamais une écriture : c'est une approximation prudente.
    matches = tuple(re.finditer(_FUNCTION, text))
    if len(matches) > 4096:
        raise ValueError(f"{path} : trop de fonctions C")
    return [
        (match[1], text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)])
        for index, match in enumerate(matches)
    ]
