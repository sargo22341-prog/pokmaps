"""Numéros de scripts réservés du moteur DS : dresseurs, objets au sol et objets cachés.

Un événement désigne son script par un numéro. Sous 2000, c'est un script du lieu ; au-delà, le moteur choisit
un fichier commun par tranche (ScriptContext_LoadAndOffsetID de Platine, LoadScriptsAndMessagesByMapId de
Diamant/Perle) : 3000 et 5000 pour les dresseurs (premier et second d'un combat à deux), 7000 pour les objets au
sol, 8000 pour les objets cachés, jusqu'à 8800. Platine nomme ces tranches (include/script_manager.h et
src/script_manager.c) ; Diamant/Perle les écrit en assembleur, dont la forme est vérifiée instruction par
instruction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_engine_text import asm_function, c_function
from .pret_gen4_source import c_defines, metang_enum, read_text

_DP_SCRIPTS = "arm9/asm/unk_02038C78.s"
# LoadScriptsAndMessagesByMapId : tranche des objets cachés (0x7D << 6 = 8000), bornée par la suivante (8800),
# puis tranche des objets au sol (7000) ; chaque fois le fichier de scripts chargé (0x176, 0x172).
_DP_CHUNKS = (
    (("ldr r2, _0203928C", "cmp r4, r2", "blo _02039134"), "_0203928C: .word 0x00002260"),
    (
        ("mov r2, #0x7d", "lsl r2, r2, #0x6", "cmp r4, r2", "blo _02039152", "ldr r2, _02039294"),
        "_02039294: .word 0x00000176",
    ),
    (("ldr r5, _02039298", "cmp r4, r5", "blo _0203916C", "ldr r2, _0203929C"), "_0203929C: .word 0x00000172"),
    # Tranche des scripts communs (0xBB8 >> 2 = 750… puis 2000 = 0x7D << 4), fichier 0xCD.
    (("lsr r2, r2, #0x2", "cmp r4, r2", "blo _020391EE", "mov r2, #0xcd", "mov r3, #0xc7"), "mov r0, #0x7d"),
)
# sub_020395F4 : numéro de dresseur d'un script de la tranche 3000 (moins 0xBB7) ou 5000 (moins 0x1387).
_DP_TRAINER_ID = (
    "ldr r1, _02039610",
    "cmp r0, r1",
    "bhs _02039604",
    "ldr r1, _02039614",
    "sub r0, r0, r1",
    "_02039610: .word 0x00001388",
    "_02039614: .word 0x00000BB7",
)
# sub_02039694 : drapeau d'un objet caché = numéro de script - 0x1C66.
_DP_HIDDEN_FLAG = ("ldr r1, _020396A0", "sub r0, r0, r1", "_020396A0: .word 0x00001C66")
_DP_VALUES = {"common": 2000, "single": 3000, "double": 5000, "visible": 7000, "hidden": 8000, "hidden_end": 8800}
_DP_FILES = {"common": 0xCD, "visible": 0x172}
_DP_HIDDEN_FLAG_BASE = 8000 - 0x1C66


@dataclass(frozen=True)
class ScriptIds:
    common: int
    common_file: int  # fichier des scripts communs (numéro des en-têtes de lieux)
    single: int
    double: int
    visible: int
    hidden: int
    hidden_end: int
    visible_file: int  # fichier de scripts des objets au sol (numéro des en-têtes de lieux)
    hidden_flag_base: int  # drapeau d'un objet caché = numéro de script - hidden + hidden_flag_base
    trainer_flag_base: int | None  # drapeau « dresseur battu » = base + numéro (Platine) ; None si non lu

    def trainer(self, script: int) -> tuple[int, bool] | None:
        """(numéro du dresseur, second d'un combat à deux) d'un script de dresseur, sinon None."""
        if self.single <= script < self.double:
            return script - self.single + 1, False
        if self.double <= script < self.visible:
            return script - self.double + 1, True
        return None


def read_script_ids(root: Path, repo: str, scripts_order: dict[str, int] | None) -> ScriptIds:
    if repo == "pokeplatinum" and scripts_order is not None:
        return _platinum(root, scripts_order)
    if repo == "pokediamond":
        return _diamond_pearl(root)
    raise ValueError(f"Dépôt de scripts DS inconnu : {repo}")


def _platinum(root: Path, scripts_order: dict[str, int]) -> ScriptIds:
    offsets = c_defines(root / "include/script_manager.h", "SCRIPT_ID_OFFSET_")
    manager = read_text(root / "src/script_manager.c")
    files = dict(re.findall(r"Entry\(SCRIPT_ID_OFFSET_(\w+),\s*(\w+),", manager))
    body = c_function(manager, "Script_GetTrainerID", "src/script_manager.c")
    expected = (
        "return scriptID - SCRIPT_ID_OFFSET_SINGLE_BATTLES + 1;",
        "return scriptID - SCRIPT_ID_OFFSET_DOUBLE_BATTLES + 1;",
    )
    if any(" ".join(line.split()) not in " ".join(body.split()) for line in expected):
        raise ValueError(f"{root} : Script_GetTrainerID modifiée")
    if files.get("VISIBLE_ITEMS") not in scripts_order or files.get("COMMON_SCRIPTS") not in scripts_order:
        raise ValueError(f"{root} : fichier des objets au sol ou des scripts communs introuvable")
    flags = metang_enum(root / "generated/vars_flags.txt")
    return ScriptIds(
        offsets["SCRIPT_ID_OFFSET_COMMON_SCRIPTS"],
        scripts_order[files["COMMON_SCRIPTS"]],
        offsets["SCRIPT_ID_OFFSET_SINGLE_BATTLES"],
        offsets["SCRIPT_ID_OFFSET_DOUBLE_BATTLES"],
        offsets["SCRIPT_ID_OFFSET_VISIBLE_ITEMS"],
        offsets["SCRIPT_ID_OFFSET_HIDDEN_ITEMS"],
        offsets["SCRIPT_ID_OFFSET_SAFARI_GAME"],
        scripts_order[files["VISIBLE_ITEMS"]],
        flags["HIDDEN_ITEM_FLAGS_START"],
        flags["TRAINER_DEFEATED_FLAGS_START"],
    )


def _diamond_pearl(root: Path) -> ScriptIds:
    text = read_text(root / _DP_SCRIPTS)
    loader = asm_function(text, "LoadScriptsAndMessagesByMapId", _DP_SCRIPTS)
    for sequence, pool in _DP_CHUNKS:
        if not _contains(loader, sequence) or pool not in loader:
            raise ValueError(f"{root / _DP_SCRIPTS} : tranche de scripts modifiée : {sequence[0]}")
    for label, lines in (("sub_020395F4", _DP_TRAINER_ID), ("sub_02039694", _DP_HIDDEN_FLAG)):
        body = asm_function(text, label, _DP_SCRIPTS)
        if any(line not in body for line in lines):
            raise ValueError(f"{root / _DP_SCRIPTS} : fonction {label} modifiée")
    values = _DP_VALUES
    return ScriptIds(
        values["common"],
        _DP_FILES["common"],
        values["single"],
        values["double"],
        values["visible"],
        values["hidden"],
        values["hidden_end"],
        _DP_FILES["visible"],
        _DP_HIDDEN_FLAG_BASE,
        None,
    )


def _contains(lines: list[str], sequence: tuple[str, ...]) -> bool:
    return any(tuple(lines[index : index + len(sequence)]) == sequence for index in range(len(lines)))
