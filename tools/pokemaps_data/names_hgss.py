"""Noms français HGSS par identifiant natif, sans confondre les numéros d'objets PokéAPI."""

import re
from pathlib import Path

from .catalog_pokemon_hgss import french_constants
from .pokeapi import PokeApi
from .pret_hgss_trainers import item_constants
from .sources import POKEAPI_COMMIT


def native_names(root: Path) -> dict:
    api = PokeApi(root.parent / f"pokeapi-{POKEAPI_COMMIT[:12]}")
    translated = french_constants(api)
    normalized = {re.sub(r"[^A-Z0-9]", "", key): value for key, value in translated.items()}
    aliases = {
        "ITEM_PARLYZ_HEAL": "ITEM_PARALYZE_HEAL",
        "ITEM_X_SPECIAL": "ITEM_X_SP_ATK",
        "ITEM_DOWSING_MCHN": "ITEM_DOWSING_MACHINE",
        "ITEM_YLW_APRICORN": "ITEM_YELLOW_APRICORN",
        "ITEM_BLU_APRICORN": "ITEM_BLUE_APRICORN",
        "ITEM_GRN_APRICORN": "ITEM_GREEN_APRICORN",
        "ITEM_PNK_APRICORN": "ITEM_PINK_APRICORN",
        "ITEM_WHT_APRICORN": "ITEM_WHITE_APRICORN",
        "ITEM_BLK_APRICORN": "ITEM_BLACK_APRICORN",
    }
    items = {0: "Aucun"}
    for constant, native_id in item_constants(root).items():
        if constant.startswith("ITEM_UNUSED_") or constant == "ITEM_NONE":
            continue
        key = re.sub(r"[^A-Z0-9]", "", aliases.get(constant, constant))
        if key not in normalized:
            raise ValueError(f"HGSS : objet sans nom français : {constant}")
        items[native_id] = normalized[key]
    return dict(
        items=items,
        species=api.names("pokemon_species_names", "pokemon_species_id"),
        moves=api.names("move_names", "move_id"),
        source=dict(
            commit=POKEAPI_COMMIT, files=["item_names.csv", "items.csv", "pokemon_species_names.csv", "move_names.csv"]
        ),
    )
