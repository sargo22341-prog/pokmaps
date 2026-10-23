"""Comparaison exhaustive des tables d'évolution DS et des conditions conservées de PokéAPI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_gen3_evolution import EvolutionRules
from .pret_identifiers import species_identifier
from .pret_items_gen4 import ds_item_id

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

_DP_METHODS = {
    "EVO_FRIENDSHIP": "EVO_LEVEL_HAPPINESS",
    "EVO_FRIENDSHIP_DAY": "EVO_LEVEL_HAPPINESS_DAY",
    "EVO_FRIENDSHIP_NIGHT": "EVO_LEVEL_HAPPINESS_NIGHT",
    "EVO_BEAUTY": "EVO_LEVEL_BEAUTY",
    "EVO_LEVEL_PID_HI": "EVO_LEVEL_PID_HIGH",
    "EVO_LEVEL_PID_LO": "EVO_LEVEL_PID_LOW",
    "EVO_STONE": "EVO_USE_ITEM",
    "EVO_STONE_MALE": "EVO_USE_ITEM_MALE",
    "EVO_STONE_FEMALE": "EVO_USE_ITEM_FEMALE",
    "EVO_TRADE_ITEM": "EVO_TRADE_WITH_HELD_ITEM",
    "EVO_ITEM_DAY": "EVO_LEVEL_WITH_HELD_ITEM_DAY",
    "EVO_ITEM_NIGHT": "EVO_LEVEL_WITH_HELD_ITEM_NIGHT",
    "EVO_HAS_MOVE": "EVO_LEVEL_KNOW_MOVE",
    "EVO_OTHER_PARTY_MON": "EVO_LEVEL_SPECIES_IN_PARTY",
    "EVO_CORONET": "EVO_LEVEL_MAGNETIC_FIELD",
    "EVO_ETERNA": "EVO_LEVEL_MOSS_ROCK",
    "EVO_ROUTE217": "EVO_LEVEL_ICE_ROCK",
}
_LEVEL_METHODS = frozenset(
    {
        "EVO_LEVEL",
        "EVO_LEVEL_NINJASK",
        "EVO_LEVEL_MALE",
        "EVO_LEVEL_FEMALE",
        "EVO_LEVEL_ATK_GT_DEF",
        "EVO_LEVEL_ATK_EQ_DEF",
        "EVO_LEVEL_ATK_LT_DEF",
        "EVO_LEVEL_PID_LOW",
        "EVO_LEVEL_PID_HIGH",
    }
)
_METHODS = frozenset(_DP_METHODS.values()) | _LEVEL_METHODS | {"EVO_TRADE", "EVO_LEVEL_SHEDINJA"}


def read_ds_evolution_rules(root: Path, repo: str) -> EvolutionRules:
    relative = "src/pokemon.c" if repo in {"pokeplatinum", "pokeheartgold"} else "arm9/src/pokemon.c"
    if (root / relative).stat().st_size > 4 * 1024 * 1024:
        raise ValueError(f"{root / relative} : moteur DS trop volumineux")
    text = (root / relative).read_text(encoding="utf-8")
    if repo == "pokeplatinum":
        header = (root / "include/constants/pokemon.h").read_text(encoding="utf-8")
        found = re.findall(r"#define EVOLVE_FRIENDSHIP_THRESHOLD (\d+)", header)
        if len(found) != 1 or text.count("EVOLVE_FRIENDSHIP_THRESHOLD <= monFriendship") != 3:
            raise ValueError(f"{root} : seuil de bonheur DS inconnu")
        threshold = int(found[0])
    elif repo in {"pokediamond", "pokeheartgold"}:
        body = text if repo == "pokeheartgold" else text[text.index("struct Evolution *evoTable") :]
        found = re.findall(r"friendship >= (\d+)", body)
        if len(found) != 3 or len(set(found)) != 1:
            raise ValueError(f"{root} : seuil de bonheur DS inconnu")
        threshold = int(found[0])
    else:
        raise ValueError(f"Dépôt d'évolution DS inconnu : {repo}")
    return EvolutionRules(threshold, True)


def compare_ds_evolutions(builder: DatabaseBuilder) -> None:
    species = {r["identifier"]: i for i, r in builder.species.items()}
    extras = {r[0]: r[1:] for r in builder.pokemon.evolution_requirement_rows}
    for vg, profiles in builder.ds_species.items():
        expected = set()
        for name, profile in profiles.items():
            for method, param, target in profile.evolutions:
                conditions = _pret_conditions(builder, _DP_METHODS.get(method, method), param)
                expected.add((species[name], species[species_identifier(target)], *conditions))
        actual = set()
        for row in builder.pokemon.evolution_rows:
            if row[1] != vg:
                continue
            extra = extras.get(row[0], (None,) * 6)
            actual.add((*row[2:], *extra[:3], extra[3] or None))
        if expected != actual:
            raise ValueError(
                f"Évolutions DS du groupe {vg} : pret seul {expected - actual}, PokéAPI seul {actual - expected}"
            )


def _pret_conditions(builder: DatabaseBuilder, method: str, param: int | str) -> tuple:
    # Ordre des colonnes d'evolution après l'espèce cible, puis lieu, sexe, équipe, proximité de pierre.
    values: list = ["level-up", *[None] * 10, *[None] * 4]
    if method not in _METHODS:
        raise ValueError(f"Méthode d'évolution DS inconnue : {method} ({param})")
    if method in _LEVEL_METHODS:
        values[1] = int(param)
        if method.endswith(("_MALE", "_FEMALE")):
            values[12] = 2 if method.endswith("_MALE") else 1
        if "_ATK_" in method:
            values[9] = {"GT": 1, "EQ": 0, "LT": -1}[method.split("_")[-2]]
        if "_PID_" in method:
            values[10] = 50
    elif method.startswith("EVO_LEVEL_HAPPINESS"):
        values[4] = 220
        values[5] = "day" if method.endswith("_DAY") else "night" if method.endswith("_NIGHT") else None
    elif (
        method.startswith("EVO_USE_ITEM")
        or method == "EVO_TRADE_WITH_HELD_ITEM"
        or method.startswith("EVO_LEVEL_WITH_HELD_ITEM")
    ):
        values = _item_conditions(builder, method, param, values)
    elif method == "EVO_TRADE":
        values[0] = "trade"
    elif method == "EVO_LEVEL_SHEDINJA":
        values[0] = "shed"
    elif method == "EVO_LEVEL_BEAUTY":
        values[8] = int(param)
    elif method == "EVO_LEVEL_KNOW_MOVE":
        values[6] = builder.moves.move_id(str(param).removeprefix("MOVE_").lower().replace("_", "-"))
    elif method == "EVO_LEVEL_SPECIES_IN_PARTY":
        species = {r["identifier"]: i for i, r in builder.species.items()}
        values[13] = species[species_identifier(str(param).removeprefix("SPECIES_"))]
    elif method in {"EVO_LEVEL_MAGNETIC_FIELD", "EVO_LEVEL_MOSS_ROCK", "EVO_LEVEL_ICE_ROCK"}:
        values[11] = {"EVO_LEVEL_MAGNETIC_FIELD": 10, "EVO_LEVEL_MOSS_ROCK": 8, "EVO_LEVEL_ICE_ROCK": 48}[method]
        values[14] = 1 if method != "EVO_LEVEL_MAGNETIC_FIELD" else None
    else:
        raise ValueError(f"Méthode d'évolution DS inconnue : {method} ({param})")
    return tuple(values)


def _item_conditions(builder: DatabaseBuilder, method: str, param: int | str, values: list) -> list:
    if isinstance(param, int):
        indices = {
            int(r["game_index"]): int(r["item_id"])
            for r in builder.api.table("item_game_indices")
            if r["generation_id"] == "4"
        }
        item = indices[param]
    else:
        item = ds_item_id(builder, param)
    if method.startswith("EVO_USE_ITEM"):
        values[0], values[2] = "use-item", item
        if method.endswith(("_MALE", "_FEMALE")):
            values[12] = 2 if method.endswith("_MALE") else 1
    else:
        values[3] = item
        if method == "EVO_TRADE_WITH_HELD_ITEM":
            values[0] = "trade"
        else:
            values[5] = "day" if method.endswith("_DAY") else "night"
    return values
