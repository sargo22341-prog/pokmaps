"""Personnages et Pokémon que le moteur de Platine ajoute lui-même au Monde Distorsion.

Les lieux du Monde Distorsion n'ont presque aucun événement dans leurs fichiers : src/overlay009/ov9_02249960.c les
pose depuis des tables C (DistWorldObjectEvent), rangées par lieu dans sMapObjectEvents. Chaque entrée garde un
événement de personnage ordinaire (objEvent) et la condition qui l'affiche (flagCond, flagCondVal) :
FLAG_COND_WORLD_PROGRESS_EQ, _LEQ et _GEQ comparent VAR_DISTORTION_WORLD_PROGRESS
(SystemVars_GetDistortionWorldProgress) à une étape de l'énumération DistWorldProgress.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import c_function, c_initializer
from .pret_gen4_flow_chains import Condition
from .pret_gen4_source import c_defines, c_enum, metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

_SOURCE = "src/overlay009/ov9_02249960.c"
_CONSTANTS = "include/constants/distortion_world.h"
_PROGRESS_VAR = "VAR_DISTORTION_WORLD_PROGRESS"
_OPERATORS = {
    "FLAG_COND_WORLD_PROGRESS_EQ": "=",
    "FLAG_COND_WORLD_PROGRESS_LEQ": "<=",
    "FLAG_COND_WORLD_PROGRESS_GEQ": ">=",
}
# Hauteur d'un événement : (case << 4) * FX32_ONE, comme ObjectEvent.y.
_HEIGHT = re.compile(r"\((\d+) << 4\) \* FX32_ONE")
_FX32_ONE = 4096
_MAX_OBJECTS = 256
_SCRIPT_ID = re.compile(r"SCRIPT_ID\((\w+), (\d+)\)")


@dataclass(frozen=True)
class _Constants:
    progress_var: int
    progress: dict[str, int]  # étapes DistWorldProgress
    flags: dict[str, int]  # drapeaux et variables (generated/vars_flags.txt)
    offsets: dict[str, int]  # SCRIPT_ID_OFFSET_… (include/script_manager.h)


@dataclass(frozen=True)
class DistortionObject:
    header: str  # constante MAP_HEADER_… du lieu
    name: str  # nom de la table C, pour les messages
    script: int | None  # nombre, ou SCRIPT_ID(TRANCHE, n) résolu ; None si absent
    hidden_flag: int | None  # drapeau de masquage, None s'il n'en a pas
    x: int | None
    z: int | None
    y: int | None  # unités fx32, comme ObjectEvent.y
    flag_condition: str  # FLAG_COND_… : FLAG_COND_NONE pour un personnage toujours présent
    conditions: tuple[Condition, ...]  # traduction des conditions d'avancement, vide sinon


def read_distortion_objects(repo: Gen4PretRepo) -> tuple[DistortionObject, ...]:
    if not repo.platinum:
        raise ValueError(f"{repo.root} : le Monde Distorsion n'existe qu'en Platine")
    text = read_text(repo.root / _SOURCE)
    body = c_function(
        read_text(repo.root / "src/system_vars.c"), "SystemVars_GetDistortionWorldProgress", "system_vars.c"
    )
    if _PROGRESS_VAR not in body:
        raise ValueError(f"{repo.root} : avancement du Monde Distorsion lu ailleurs que dans {_PROGRESS_VAR}")
    flags = metang_enum(repo.root / "generated/vars_flags.txt")
    constants = _Constants(
        flags[_PROGRESS_VAR],
        c_enum(repo.root / _CONSTANTS, "DistWorldProgress"),
        flags,
        c_defines(repo.root / "include/script_manager.h", "SCRIPT_ID_OFFSET_"),
    )
    table = re.findall(r"\{\s*(MAP_HEADER_\w+),\s*(\w+)\s*\}", c_initializer(text, "sMapObjectEvents", _SOURCE))
    if not table or table[-1] != ("MAP_HEADER_INVALID", "NULL"):
        raise ValueError(f"{repo.root / _SOURCE} : table sMapObjectEvents sans fin")
    result = []
    for header, listing in table[:-1]:
        names = re.findall(r"&(\w+)", c_initializer(text, listing, _SOURCE))
        result += [_object(text, header, name, constants) for name in names]
    if not result or len(result) > _MAX_OBJECTS:
        raise ValueError(f"{repo.root / _SOURCE} : {len(result)} personnages du Monde Distorsion")
    return tuple(result)


def _object(text: str, header: str, name: str, constants: _Constants) -> DistortionObject:
    match = re.search(rf"static const DistWorldObjectEvent {name} = \{{(.*?)\n\}};", text, re.DOTALL)
    if match is None:
        raise ValueError(f"{_SOURCE} : personnage {name} introuvable")
    # Un champ par ligne ; sa valeur peut contenir des virgules (SCRIPT_ID(VISIBLE_ITEMS, 321)).
    fields = dict(re.findall(r"^\s*\.(\w+) = (.+),$", match.group(1), re.MULTILINE))
    condition, value = fields.get("flagCond"), fields.get("flagCondVal")
    if condition is None or value is None or "objEvent" not in match.group(1):
        raise ValueError(f"{_SOURCE} : personnage {name} illisible")
    conditions: tuple[Condition, ...] = ()
    if condition in _OPERATORS:
        if value not in constants.progress:
            raise ValueError(f"{_SOURCE} : {name} : étape du Monde Distorsion inconnue : {value}")
        conditions = (Condition(f"var:{constants.progress_var}", _OPERATORS[condition], constants.progress[value]),)
    height = _HEIGHT.fullmatch(fields.get("y", ""))
    y = int(height.group(1)) * 16 * _FX32_ONE if height else None
    return DistortionObject(
        header,
        name,
        _script(fields.get("script"), constants, name),
        _flag(fields.get("hiddenFlag"), constants, name),
        _number(fields.get("x")),
        _number(fields.get("z")),
        y,
        condition,
        conditions,
    )


def _script(text: str | None, constants: _Constants, name: str) -> int | None:
    found = _SCRIPT_ID.fullmatch(text or "")
    if found is None:
        return _number(text)
    offset = f"SCRIPT_ID_OFFSET_{found.group(1)}"
    if offset not in constants.offsets:
        raise ValueError(f"{_SOURCE} : {name} : tranche de scripts inconnue : {found.group(1)}")
    return constants.offsets[offset] + int(found.group(2))


def _flag(text: str | None, constants: _Constants, name: str) -> int | None:
    value = constants.flags.get(text or "", _number(text))
    if value is None:
        raise ValueError(f"{_SOURCE} : {name} : drapeau de masquage illisible : {text}")
    return value or None


def _number(text: str | None) -> int | None:
    """Entier écrit tel quel, sinon None (constante ou macro, que seules les lectures qui en ont besoin résolvent)."""
    try:
        return int(text, 0) if text is not None else None
    except ValueError:
        return None
