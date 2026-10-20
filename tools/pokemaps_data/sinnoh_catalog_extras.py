"""Noms français des fouilles, équipes et objets du Souterrain."""

from __future__ import annotations

from pathlib import Path

from .hoenn_catalog import translations
from .pokeapi import PokeApi
from .pret_identifiers import item_identifier
from .pret_sinnoh_battle import battle_catalog
from .pret_sinnoh_frontier import frontier_catalog
from .pret_sinnoh_mining import mining_catalog
from .pret_sinnoh_underground import underground_catalog


def content_extras(api: PokeApi, root: Path, platinum_root: Path, group: str) -> dict:
    platinum = group == "platinum"
    underground = underground_catalog(root, platinum_root, platinum)
    goods_names = translations("underground_goods_fr.csv", "name_fr", 132)
    trap_names = translations("underground_traps_fr.csv", "name_fr", 27)
    for key, names in (("goods", goods_names), ("traps", trap_names)):
        if set(names) != {row["identifier"] for row in underground[key]}:
            raise ValueError(f"{group} : traductions du Souterrain incomplètes : {key}")
        underground[key] = [{**row, "name": names[row["identifier"]]} for row in underground[key]]
    battles = battle_catalog(root, platinum)
    battles["sets"] = _named_sets(api, battles["sets"])
    if platinum:
        battles["frontier"] = frontier_catalog(root)
        hall = battles["frontier"]["hall"]
        hall["sets"] = _named_sets(api, hall["sets"])
    mining = mining_catalog(root, platinum_root, "platinum" if platinum else "diamond")
    item_names = api.names("item_names", "item_id")
    items = {
        row["identifier"]: item_names[int(row["id"])] for row in api.table("items") if int(row["id"]) in item_names
    }
    for row in mining:
        key = row["identifier"]
        if key.startswith("MINING_TREASURE_"):
            row["name"] = items[item_identifier(key.removeprefix("MINING_TREASURE_"), {})]
        else:
            row["name"] = _sphere_name(key)
    return {"underground": underground, "battles": battles, "mining": mining}


def _named_sets(api: PokeApi, rows: list[dict]) -> list[dict]:
    pokemon = api.names("pokemon_species_names", "pokemon_species_id")
    moves = api.names("move_names", "move_id")
    natures = translations("natures_fr.csv", "name_fr", 25)
    items = api.names("item_names", "item_id")
    native_items = {
        int(row["game_index"]): int(row["item_id"])
        for row in api.table("item_game_indices")
        if row["generation_id"] == "4"
    }
    return [
        {
            **row,
            "name": pokemon[row["species"]],
            "move_names": [moves[i] for i in row["moves"] if i],
            "nature_name": natures[str(row["nature"])],
            "item_name": items[native_items[row["item"]]] if row["item"] else "",
        }
        for row in rows
    ]


def _sphere_name(key: str) -> str:
    names = {"PRISM": "prisme", "PALE": "pâle", "RED": "rouge", "BLUE": "bleue", "GREEN": "verte"}
    _, size, color, suffix = key.split("_")
    if size not in {"SMALL", "LARGE"} or color not in names or suffix != "SPHERE":
        raise ValueError(f"Sphère DS inconnue : {key}")
    return f"Sphère {names[color]} ({'petite' if size == 'SMALL' else 'grande'})"
