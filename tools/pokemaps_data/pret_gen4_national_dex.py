"""Déblocage du Pokédex National, lu dans les scripts et le moteur de chaque jeu DS.

Le seul script qui active le Pokédex National (GetSetNationalDexEnabled 1 en Platine, ScrCmd_NationalDex 1 en
Diamant/Perle) appartient au laboratoire du Prof. Sorbier à Littorella. Chaque chemin qui y mène passe par la
vérification du Pokédex de Sinnoh : CheckLocalDexCompleted (Platine) ou ScrCmd_CheckSinnohDexComplete
(Diamant/Perle) doit répondre vrai. Le moteur compte les Pokémon vus du Pokédex de Sinnoh :

- Platine, Pokedex_LocalDexCompleted : au moins LOCAL_DEX_GOAL = REGIONAL_DEX_COUNT - NUM_EXCLUDED_LOCAL, soit les
  210 espèces de res/pokemon/sinnoh_pokedex.json (sa première ligne tient la place du numéro 0), sans exclusion ;
- Diamant/Perle, Pokedex_SinnohDexIsComplete : au moins 150, Manaphy n'étant pas compté
  (Pokedex_SpeciesIsNotSinnohMythical).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import c_function
from .pret_gen4_flow import NATIONAL_DEX
from .pret_gen4_flow_chains import Chains, Condition
from .pret_gen4_source import read_json_list, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header

_ENABLE = 1
_CHECKS = {"platinum": "CheckLocalDexCompleted", "diamond-pearl": "ScrCmd_CheckSinnohDexComplete"}


@dataclass(frozen=True)
class NationalDexUnlock:
    headers: tuple[str, ...]  # lieux dont le fichier de scripts active le Pokédex National
    step: str
    # Conditions de chaque chemin qui mène à l'activation, dans l'ordre du script.
    paths: tuple[tuple[Condition, ...], ...]
    check: str  # commande qui vérifie le Pokédex de Sinnoh
    seen_required: int  # Pokémon du Pokédex de Sinnoh à avoir vus
    excluded: tuple[str, ...]  # espèces du Pokédex de Sinnoh qui ne comptent pas


def read_national_dex(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> NationalDexUnlock:
    sites = [
        (index, step)
        for index, flow in repo.flows.items()
        for step in flow.steps.values()
        if step.command == NATIONAL_DEX and step.arguments[0] == _ENABLE
    ]
    if len(sites) != 1:
        raise ValueError(f"{repo.root} : une seule activation du Pokédex National attendue, {len(sites)} lues")
    index, step = sites[0]
    places = tuple(sorted(header.constant for header in headers.values() if header.scripts == index))
    if not places:
        raise ValueError(f"{repo.root} : activation du Pokédex National hors des lieux retenus")
    check = _CHECKS[repo.variant]
    paths = Chains(repo.flows[index]).paths(step.key)
    if not paths or any(Condition(check, "=", 1) not in path for path in paths):
        raise ValueError(f"{repo.root} : un chemin active le Pokédex National sans {check}")
    required, excluded = _platinum_goal(repo) if repo.platinum else _dp_goal(repo)
    return NationalDexUnlock(places, step.source, paths, check, required, excluded)


def _platinum_goal(repo: Gen4PretRepo) -> tuple[int, tuple[str, ...]]:
    header = read_text(repo.root / "include/pokedex.h")
    body = c_function(read_text(repo.root / "src/pokedex.c"), "Pokedex_LocalDexCompleted", "pokedex.c")
    expected = (
        "#define NUM_EXCLUDED_LOCAL    0",
        "#define LOCAL_DEX_GOAL        (REGIONAL_DEX_COUNT - NUM_EXCLUDED_LOCAL)",
    )
    if any(line not in header for line in expected) or "numSeen >= LOCAL_DEX_GOAL" not in body:
        raise ValueError(f"{repo.root} : règle du Pokédex de Sinnoh modifiée (Pokedex_LocalDexCompleted)")
    path = repo.root / "res/pokemon/sinnoh_pokedex.json"
    listing = read_json_list(path)
    if not listing or not all(isinstance(row, str) and row.startswith("SPECIES_") for row in listing):
        raise ValueError(f"{path} : liste du Pokédex de Sinnoh illisible")
    # dexproc.c : REGIONAL_DEX_COUNT = nombre de lignes - 1 (la première tient la place du numéro 0).
    return len(listing) - 1, ()


def _dp_goal(repo: Gen4PretRepo) -> tuple[int, tuple[str, ...]]:
    text = read_text(repo.root / "arm9/src/pokedex.c")
    goal = re.fullmatch(
        r"\s*return Pokedex_CountSinnohDexSeen_OmitMythicals\(pokedex\) >= (\d+);\s*",
        c_function(text, "Pokedex_SinnohDexIsComplete", "pokedex.c"),
    )
    omitted = re.findall(
        r"species == (SPECIES_\w+)", c_function(text, "Pokedex_SpeciesIsNotSinnohMythical", "pokedex.c")
    )
    count = c_function(text, "Pokedex_CountSinnohDexSeen_OmitMythicals", "pokedex.c")
    if goal is None or not omitted or "Pokedex_SpeciesIsNotSinnohMythical" not in count:
        raise ValueError(f"{repo.root} : règle du Pokédex de Sinnoh modifiée (Pokedex_SinnohDexIsComplete)")
    return int(goal.group(1)), tuple(omitted)
