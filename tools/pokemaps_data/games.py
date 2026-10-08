"""Jeux pris en charge par l'application.

Chaque entrée choisit les versions PokéAPI, le format pret, les régions et les jaquettes du jeu.
PokéAPI fournit les données Pokémon et les lieux ; les sources pret complètent les mécaniques et
offres du jeu, génèrent ses cartes et fournissent les rencontres aléatoires de la 2e génération.
Les identifiants des groupes de versions sont ceux de PokéAPI (table version_groups).
Un nouveau jeu reste dans GAMES_IN_PROGRESS jusqu'à sa validation complète (voir README.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PretFormat(Enum):
    """Format des sources d'un désassemblage pret : chaque format a son lecteur."""

    # pokered, pokeyellow : en-têtes data/maps/headers, objets data/maps/objects, textes TEXT_…
    GEN1 = "gen1"
    # pokegold, pokecrystal : en-têtes data/maps/maps.asm, événements maps/<Carte>.asm, scripts d'événements.
    GEN2 = "gen2"


@dataclass(frozen=True)
class VersionCover:
    """Jaquette dessinée par l'application pour une version : le Pokémon de sa jaquette et sa couleur."""

    # Identifiant PokéAPI de la version (ex. "red").
    version: str
    # Identifiant PokéAPI de l'espèce mise en avant sur la jaquette (ex. "charizard").
    mascot: str
    # Couleur de la version, 0xRRGGBB.
    color: int


@dataclass(frozen=True)
class Region:
    """Région d'un jeu : ses villes et routes forment une carte du monde, construite depuis `start_map`."""

    # Constante de la carte du monde (ex. "KANTO") ; son nom français est dans tools/data/maps.csv.
    const: str
    # Ville d'où partent les connexions qui assemblent la carte du monde.
    start_map: str
    # Numéro de la carte du monde dans la base, hors de la plage des numéros des cartes pret.
    number: int


KANTO = Region("KANTO", "PALLET_TOWN", 999)
JOHTO = Region("JOHTO", "NEW_BARK_TOWN", 998)


@dataclass(frozen=True)
class Game:
    # Identifiant PokéAPI du groupe de versions (ex. "red-blue").
    version_group: str
    # Désassemblage pret d'où sont générées les cartes (cf. sources.PRET_COMMITS).
    pret_repo: str
    # Versions PokéAPI du jeu et symbole qui les distingue dans pret (IF DEF(_RED) : propre à Rouge).
    pret_versions: tuple[tuple[str, str], ...]
    # Famille de cartes : les jeux d'une même famille partagent leurs plans (Rouge, Bleu et Jaune ; Or, Argent et
    # Cristal), donc les emplacements de Pokémon retouchés dans tools/data/map_spots.csv.
    map_family: str
    # Jaquette de chaque version du jeu, dans l'ordre de pret_versions.
    covers: tuple[VersionCover, ...]
    # Format des sources pret, qui choisit le lecteur des cartes, des dresseurs et des attaques.
    pret_format: PretFormat
    # Régions du jeu, une carte du monde chacune.
    regions: tuple[Region, ...]


_GEN1_GAMES: tuple[Game, ...] = (
    Game(
        "red-blue",
        "pokered",
        (("red", "_RED"), ("blue", "_BLUE")),
        "red-blue-yellow",
        (VersionCover("red", "charizard", 0xD8302A), VersionCover("blue", "blastoise", 0x2A63C4)),
        PretFormat.GEN1,
        (KANTO,),
    ),
    Game(
        "yellow",
        "pokeyellow",
        (("yellow", "_YELLOW"),),
        "red-blue-yellow",
        (VersionCover("yellow", "pikachu", 0xF2C21B),),
        PretFormat.GEN1,
        (KANTO,),
    ),
)

GOLD_SILVER = Game(
    "gold-silver",
    "pokegold",
    (("gold", "_GOLD"), ("silver", "_SILVER")),
    "gold-silver-crystal",
    (VersionCover("gold", "ho-oh", 0xC9A227), VersionCover("silver", "lugia", 0x9DA9B5)),
    PretFormat.GEN2,
    (JOHTO, KANTO),
)

CRYSTAL = Game(
    "crystal",
    "pokecrystal",
    (("crystal", "_CRYSTAL"),),
    "gold-silver-crystal",
    (VersionCover("crystal", "suicune", 0x59BFCB),),
    PretFormat.GEN2,
    (JOHTO, KANTO),
)
GAMES: tuple[Game, ...] = (*_GEN1_GAMES, GOLD_SILVER, CRYSTAL)
# Les futurs jeux restent dans l’aperçu jusqu’à leur prise en charge par l’application.
GAMES_IN_PROGRESS: tuple[Game, ...] = ()
# Tous les jeux générés : ceux de l'application, puis ceux en cours d'intégration.
ALL_GAMES: tuple[Game, ...] = (*GAMES, *GAMES_IN_PROGRESS)


def map_families(games: tuple[Game, ...] = ALL_GAMES) -> dict[str, tuple[str, ...]]:
    """Groupes de versions de chaque famille de cartes, dans l'ordre de `games`."""
    families: dict[str, tuple[str, ...]] = {}
    for game in games:
        families[game.map_family] = (*families.get(game.map_family, ()), game.version_group)
    return families


def complete_families(games: tuple[Game, ...]) -> dict[str, tuple[str, ...]]:
    """Familles de cartes dont tous les jeux sont dans `games` : leurs fichiers relus se vérifient en entier."""
    families = map_families((*ALL_GAMES, *(game for game in games if game not in ALL_GAMES)))
    built = {game.version_group for game in games}
    return {family: groups for family, groups in families.items() if set(groups) <= built}


# Méthodes de rencontre « uniques » (un Pokémon donné, fixe, échangé ou errant) : pas de probabilité,
# on compte le nombre d'exemplaires. Toutes les autres sont des rencontres aléatoires dont
# les probabilités (rarity) d'une zone totalisent 100 %.
ONE_OFF_METHODS = frozenset({"gift", "gift-egg", "static", "pokeflute", "npc-trade", "squirt-bottle", "roaming-grass"})
