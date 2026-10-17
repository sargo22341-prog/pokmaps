"""Lecture de fragments du moteur DS : fonctions C de Platine et fonctions assembleur Thumb de Diamant/Perle.

Les règles sauvages du moteur (probabilités des emplacements, cases, tables d'en-têtes) se lisent dans ces
fonctions. Chaque lecture vérifie la forme attendue et arrête la génération en nommant la fonction qui diffère.
"""

from __future__ import annotations

import re
from itertools import pairwise

_C_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_ASM_COMMENT = re.compile(r";[^\n]*")
_ASM_FUNCTION = re.compile(r"^\s*(?:thumb|arm)_func_start\s+(\w+)\s*$", re.MULTILINE)
_ASM_BYTES = re.compile(r"^\s*\.byte\s+(.*)$")
_ASM_WORDS = re.compile(r"^\s*\.word\s+(.*)$")
# Une fonction du moteur tient en quelques centaines de lignes : au-delà, la lecture s'est trompée de bornes.
_MAX_FUNCTION_LINES = 2000


def c_function(text: str, name: str, where: str) -> str:
    """Corps (entre accolades) de la fonction C `name`, sans commentaires."""
    source = _C_COMMENT.sub("", text)
    matches = list(re.finditer(rf"^[\w \t\*]*\b{re.escape(name)}\s*\([^;{{]*\)\s*\{{", source, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f"{where} : fonction {name} introuvable ou répétée")
    start = matches[0].end()
    depth = 1
    for position in range(start, min(len(source), start + 200_000)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start:position]
    raise ValueError(f"{where} : fonction {name} non refermée")


def c_initializer(text: str, name: str, where: str) -> str:
    """Contenu de l'initialiseur `name[...] = { ... };` (une ou plusieurs dimensions), sans commentaires."""
    source = _C_COMMENT.sub("", text)
    match = re.search(rf"\b{re.escape(name)}(?:\s*\[[^\]]*\])+\s*=\s*\{{(.*?)\}};", source, re.DOTALL)
    if match is None:
        raise ValueError(f"{where} : table {name} introuvable")
    return match.group(1)


def asm_function(text: str, label: str, where: str) -> list[str]:
    """Instructions de la fonction assembleur `label`, jusqu'au début de la fonction suivante."""
    starts = [match for match in _ASM_FUNCTION.finditer(text) if match.group(1) == label]
    if len(starts) != 1:
        raise ValueError(f"{where} : fonction {label} introuvable ou répétée")
    following = _ASM_FUNCTION.search(text, starts[0].end())
    end = following.start() if following else len(text)
    body = text[starts[0].end() : end].split(".section")[0]
    lines = [line.strip() for line in _ASM_COMMENT.sub("", body).splitlines() if line.strip()]
    if not lines or len(lines) > _MAX_FUNCTION_LINES or lines[0] != f"{label}:":
        raise ValueError(f"{where} : fonction {label} illisible")
    return lines[1:]


def asm_data(text: str, label: str, where: str) -> bytes:
    """Octets de la donnée `label` (`.byte`, ou `.word` d'entiers), jusqu'à la ligne vide qui la termine."""
    match = re.search(rf"^{re.escape(label)}:[^\n]*\n((?:[ \t]*\.(?:byte|word)[^\n]*\n)+)", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"{where} : donnée {label} introuvable")
    data = bytearray()
    for line in match.group(1).splitlines():
        if found := _ASM_BYTES.match(line):
            data.extend(int(value.strip(), 0) for value in found.group(1).split(","))
        elif found := _ASM_WORDS.match(line):
            for value in found.group(1).split(","):
                data.extend(int(value.strip(), 0).to_bytes(4, "little"))
    return bytes(data)


def c_threshold_rates(body: str, variable: str, slots: int, where: str) -> tuple[int, ...]:
    """Probabilités (sur 100) des emplacements choisis par une suite de tests sur `variable`, tirée dans [0, 100) :
    `variable < N`, `variable >= N && variable < M` ou `variable == N`, l'emplacement suivant prenant le reste."""
    bounds: set[int] = set()
    for operator, value in re.findall(rf"\b{re.escape(variable)}\s*(<|>=|==)\s*(\d+)", body):
        bounds.add(int(value))
        if operator == "==":
            bounds.add(int(value) + 1)
    return _rates(bounds, slots, where)


def asm_threshold_rates(lines: list[str], register: str, slots: int, where: str) -> tuple[int, ...]:
    """Même lecture pour une fonction Thumb : `cmp REG, #N` borne un emplacement, et un `cmp` suivi de `bne` est
    un test d'égalité (l'emplacement N seul)."""
    bounds: set[int] = set()
    pattern = re.compile(rf"cmp {re.escape(register)}, #(0x[0-9a-fA-F]+|\d+)$")
    for index, line in enumerate(lines):
        if match := pattern.match(line):
            value = int(match.group(1), 0)
            if value == 100:
                continue  # Contrôle de la borne du tirage (GF_AssertFail), pas un emplacement.
            bounds.add(value)
            if index + 1 < len(lines) and lines[index + 1].startswith("bne "):
                bounds.add(value + 1)
    return _rates(bounds, slots, where)


def _rates(bounds: set[int], slots: int, where: str) -> tuple[int, ...]:
    edges = [0, *sorted(bounds), 100]
    rates = tuple(high - low for low, high in pairwise(edges))
    if len(rates) != slots or any(rate <= 0 for rate in rates) or sum(rates) != 100:
        raise ValueError(f"{where} : {slots} probabilités attendues, lu {rates}")
    return rates
