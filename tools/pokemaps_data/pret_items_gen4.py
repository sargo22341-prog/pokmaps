"""Catalogue des objets DS ; les emplacements réservés du moteur ne sont pas des objets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_gen4_source import read_json
from .pret_identifiers import item_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

_UNUSED_PLATINUM = frozenset(f"ITEM_UNUSED_{index}" for index in range(113, 135))


def ds_item_id(builder: DatabaseBuilder, const: str) -> int:
    name = const.removeprefix("ITEM_")
    identifier = item_identifier(name, {})
    ids = builder.items.ids
    compact = {key.replace("-", ""): value for key, value in ids.items()}
    if identifier in ids:
        return ids[identifier]
    if identifier.replace("-", "") not in compact:
        raise ValueError(f"Objet DS inconnu de PokéAPI : {const}")
    return compact[identifier.replace("-", "")]


def ds_item_constants(root: Path, repo: str) -> tuple[str, ...]:
    if repo == "pokeplatinum":
        lines = (root / "generated/items.txt").read_text(encoding="utf-8").splitlines()
        return tuple(
            line for line in lines if line.startswith("ITEM_") and line != "ITEM_NONE" and line not in _UNUSED_PLATINUM
        )
    if repo == "pokediamond":
        rows = read_json(root / "files/itemtool/itemdata/item_data.json")["item_data"]
        return tuple(r["name"] for r in rows if r["name"] != "ITEM_NONE")
    raise ValueError(f"Dépôt d'objets DS inconnu : {repo}")


def ds_held_items(builder: DatabaseBuilder, vg: int) -> list[tuple]:
    from .pret_species_gen4 import read_ds_species

    game = builder.game_of(vg)
    common, rare = read_held_item_rates(builder.pret_root(game, "les probabilités d'objets tenus"), game.pret_repo)
    species = {r["identifier"]: i for i, r in builder.species.items()}
    rows = []
    for version in (r for r in builder.version_rows if int(r["version_group_id"]) == vg):
        profiles = builder.ds_species[vg]
        if version["identifier"] == "pearl":
            profiles = read_ds_species(builder.pret_root(game, "les objets tenus de Perle"), game.pret_repo, pearl=True)
        for name, profile in profiles.items():
            first, second = profile.held_items
            chances = ((first, 100),) if first == second else ((first, common), (second, rare))
            rows += [
                (species[name], int(version["id"]), ds_item_id(builder, item), chance)
                for item, chance in chances
                if item != "ITEM_NONE"
            ]
    return rows


def read_held_item_rates(root: Path, repo: str) -> tuple[int, int]:
    if repo not in {"pokeplatinum", "pokediamond"}:
        raise ValueError(f"Dépôt d'objets DS inconnu : {repo}")
    path = root / ("src/pokemon.c" if repo == "pokeplatinum" else "arm9/src/pokemon.c")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError(f"{path} : moteur DS trop volumineux")
    text = path.read_text(encoding="utf-8")
    table = "sHeldItemChance" if repo == "pokeplatinum" else "sItemOdds"
    found = re.findall(rf"{table}\[[^=]+?=\s*\{{\s*\{{\s*(\d+),\s*(\d+)\s*\}}", text)
    same = (
        "monItem1 == monItem2 && monItem1 != ITEM_NONE"
        if repo == "pokeplatinum"
        else "item1 == item2 && item1 != ITEM_NONE"
    )
    if len(found) != 1 or same not in text or "% 100" not in text:
        raise ValueError(f"{path} : règles d'objets tenus non reconnues")
    absent, boundary = map(int, found[0])
    if not 0 <= absent < boundary < 100:
        raise ValueError(f"{path} : probabilités d'objets tenus invalides")
    return boundary - absent, 100 - boundary
