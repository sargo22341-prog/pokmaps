"""Règles d'évolution du moteur de la 3e génération, lues dans GetEvolutionTargetSpecies (pret).

PokéAPI donne les évolutions de chaque espèce, mais pas deux règles du moteur :
- le bonheur nécessaire : `friendship >= 220` (FRIENDSHIP_EVO_THRESHOLD dans pokeemerald) ;
- les évolutions par bonheur de jour ou de nuit (Mentali, Noctali) : Rouge Feu et Vert Feuille n'ont pas d'horloge,
  leur moteur a ces deux cas en commentaire et ne fait jamais évoluer ces Pokémon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Fichier qui définit GetEvolutionTargetSpecies dans chaque dépôt.
EVOLUTION_SOURCES = {"pokeruby": "src/pokemon_3.c", "pokeemerald": "src/pokemon.c", "pokefirered": "src/pokemon.c"}
_FUNCTION = "u16 GetEvolutionTargetSpecies("
_MAX_FUNCTION_LINES = 300
_FRIENDSHIP_CASES = ("EVO_FRIENDSHIP", "EVO_FRIENDSHIP_DAY", "EVO_FRIENDSHIP_NIGHT")
_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_THRESHOLD = re.compile(r"friendship >= (\w+)")
_DEFINE = re.compile(r"^#define (\w+) (\d+)$", re.MULTILINE)


@dataclass(frozen=True)
class EvolutionRules:
    # Bonheur à partir duquel un Pokémon évolue par bonheur.
    happiness: int
    # Le moteur fait évoluer par bonheur de jour ou de nuit (horloge du jeu).
    time_of_day: bool


def read_evolution_rules(root: Path, pret_repo: str) -> EvolutionRules:
    """Règles d'évolution du dépôt `pret_repo` extrait dans `root`."""
    if pret_repo not in EVOLUTION_SOURCES:
        raise ValueError(f"Dépôt pret sans source d'évolution connue : {pret_repo}")
    path = root / EVOLUTION_SOURCES[pret_repo]
    text = path.read_text(encoding="utf-8")
    defines = {name: int(value) for name, value in _DEFINE.findall(text)}
    body = _COMMENTS.sub("", _function_body(text, path))
    thresholds = {name: _thresholds(_case(body, name, path), defines, path) for name in _FRIENDSHIP_CASES}
    values = {value for found in thresholds.values() for value in found}
    timed = [bool(thresholds[name]) for name in _FRIENDSHIP_CASES[1:]]
    if len(values) != 1 or len(thresholds["EVO_FRIENDSHIP"]) != 1 or timed[0] != timed[1]:
        raise ValueError(f"{path} : seuils de bonheur inattendus : {thresholds}")
    return EvolutionRules(values.pop(), timed[0])


def _function_body(text: str, path: Path) -> str:
    """Corps de GetEvolutionTargetSpecies, jusqu'à l'accolade fermante en début de ligne."""
    start = text.find(_FUNCTION)
    if start < 0:
        raise ValueError(f"{path} : {_FUNCTION} introuvable")
    lines = text[start:].splitlines()[:_MAX_FUNCTION_LINES]
    end = next((index for index, line in enumerate(lines) if line == "}"), None)
    if end is None:
        raise ValueError(f"{path} : fin de GetEvolutionTargetSpecies introuvable en {_MAX_FUNCTION_LINES} lignes")
    return "\n".join(lines[:end])


def _case(body: str, name: str, path: Path) -> str:
    """Instructions du cas `name` jusqu'à son `break;` ; il doit être unique dans la fonction."""
    found = re.findall(rf"case {name}:(.*?)break;", body, re.DOTALL)
    if len(found) != 1:
        raise ValueError(f"{path} : {len(found)} cas {name} dans GetEvolutionTargetSpecies")
    return found[0]


def _thresholds(body: str, defines: dict[str, int], path: Path) -> list[int]:
    values = []
    for token in _THRESHOLD.findall(body):
        if token.isdigit():
            values.append(int(token))
        elif token in defines:
            values.append(defines[token])
        else:
            raise ValueError(f"{path} : seuil de bonheur inconnu : {token}")
    return values
