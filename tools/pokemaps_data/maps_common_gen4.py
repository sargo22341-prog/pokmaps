"""Passages des scripts communs, dont l'origine dépend du contexte d'appel du moteur."""

from __future__ import annotations

import re

from .maps_passages_gen4 import Passage, _boat_macros, _diamond, _platinum
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_source import read_text

# LoadScriptsAndMessages, arm9/asm/unk_02038C78.s : archives chargées dans r2 pour les plages
# 2000 (commun), 9800 (concours), 9000 (communication) et 8800 (Centre Pokémon, sous-sol).
_DP_COMMON_TRANSPORT_ARCHIVES = (205, 206, 207, 462)


def common_passages(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    if not repo.platinum:
        return _dp_passages(repo)
    table = read_text(repo.root / "src/script_manager.c")
    names = set(re.findall(r"Entry\(SCRIPT_ID_OFFSET_\w+,\s*(scripts_\w+),", table))
    if "scripts_common" not in names:
        raise ValueError("script_manager.c : scripts communs absents")
    constants = {header.constant: index for index, header in repo.headers.items()}
    boats = _boat_macros(repo)
    result = []
    for number, script in repo.scripts.items():
        if script.name in names:
            result.extend(_platinum(None, number, script, constants, boats))
    return tuple(dict.fromkeys(result))


def _dp_passages(repo: Gen4PretRepo) -> tuple[Passage, ...]:
    path = repo.root / "arm9/asm/unk_02038C78.s"
    source = read_text(path)
    for pattern in (r"mov r2, #0xcd", r"mov r2, #0xce", r"mov r2, #0xcf", r"\.word 0x000001CE"):
        if re.search(pattern, source, re.IGNORECASE) is None:
            raise ValueError(f"{path} : chargement de scripts communs modifié : {pattern}")
    result = []
    for number in _DP_COMMON_TRANSPORT_ARCHIVES:
        if number not in repo.scripts:
            raise ValueError(f"{path} : archive de script commun absente : {number}")
        result.extend(_diamond(None, number, repo.scripts[number]))
    return tuple(dict.fromkeys(result))
