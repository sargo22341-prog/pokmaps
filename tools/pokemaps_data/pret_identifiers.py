"""Identifiants PokéAPI des objets et des Pokémon nommés par une constante pret (MOON_STONE -> moon-stone).

La plupart se déduisent de la constante ; ITEM_ALIASES et SPECIES_ALIASES relient les autres. Les objets de la
2e génération que PokéAPI a fusionnés avec leur successeur suivent PokéAPI (item_game_indices) : BERRY devient
la Baie Oran, PSNCUREBERRY la Baie Pêcha, etc. Un identifiant inconnu de PokéAPI arrête la génération
(builder_items.ItemTables).
"""

from __future__ import annotations

from collections.abc import Mapping

ITEM_ALIASES = {
    # 1re et 2e générations.
    "ELIXER": "elixir",
    "MAX_ELIXER": "max-elixir",
    "X_SPECIAL": "x-sp-atk",
    "PARLYZ_HEAL": "paralyze-heal",
    "S_S_TICKET": "ss-ticket",
    "X_DEFEND": "x-defense",
    # 2e génération : noms abrégés des constantes pret.
    "BRIGHTPOWDER": "bright-powder",
    "THUNDERSTONE": "thunder-stone",
    "ITEMFINDER": "dowsing-machine",
    "SECRETPOTION": "secret-potion",
    "TINYMUSHROOM": "tiny-mushroom",
    "SILVERPOWDER": "silver-powder",
    "TWISTEDSPOON": "twisted-spoon",
    "BLACKBELT_I": "black-belt",
    "BLACKGLASSES": "black-glasses",
    "SLOWPOKETAIL": "slowpoke-tail",
    "NEVERMELTICE": "never-melt-ice",
    "RAGECANDYBAR": "rage-candy-bar",
    "SQUIRTBOTTLE": "squirt-bottle",
    "BLU_APRICORN": "blue-apricorn",
    "YLW_APRICORN": "yellow-apricorn",
    "GRN_APRICORN": "green-apricorn",
    "WHT_APRICORN": "white-apricorn",
    "BLK_APRICORN": "black-apricorn",
    "PNK_APRICORN": "pink-apricorn",
    # 2e génération : baies fusionnées par PokéAPI avec celles de la 3e génération.
    "BERRY": "oran-berry",
    "GOLD_BERRY": "sitrus-berry",
    "PSNCUREBERRY": "pecha-berry",
    "PRZCUREBERRY": "cheri-berry",
    "BURNT_BERRY": "aspear-berry",
    "ICE_BERRY": "rawst-berry",
    "BITTER_BERRY": "persim-berry",
    "MINT_BERRY": "chesto-berry",
    "MIRACLEBERRY": "lum-berry",
    "MYSTERYBERRY": "leppa-berry",
}

# Pokémon dont la constante pret ne donne pas l'identifiant PokéAPI (orthographe de la 2e génération).
SPECIES_ALIASES = {"FARFETCH_D": "farfetchd", "MR__MIME": "mr-mime"}


def const_identifier(const: str) -> str:
    """Identifiant déduit d'une constante pret : MOON_STONE -> moon-stone."""
    return const.lower().replace("_", "-")


def item_identifier(const: str, machines: Mapping[str, str]) -> str:
    """Identifiant PokéAPI de l'objet `const` ; `machines` relie les CT / CS du jeu à leur identifiant (tm01)."""
    return machines.get(const) or ITEM_ALIASES.get(const) or const_identifier(const)


def species_identifier(const: str) -> str:
    """Identifiant PokéAPI du Pokémon `const`."""
    return SPECIES_ALIASES.get(const) or const_identifier(const)
