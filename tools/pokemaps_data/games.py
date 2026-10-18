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

from .external_events import event_locations


class PretFormat(Enum):
    """Format des sources d'un désassemblage pret : chaque format a son lecteur."""

    # pokered, pokeyellow : en-têtes data/maps/headers, objets data/maps/objects, textes TEXT_…
    GEN1 = "gen1"
    # pokegold, pokecrystal : en-têtes data/maps/maps.asm, événements maps/<Carte>.asm, scripts d'événements.
    GEN2 = "gen2"
    # pokeruby, pokeemerald, pokefirered : data/maps/<Carte>/map.json, sources C et JSON, variantes par dépôt.
    GEN3 = "gen3"
    # DS : JSON par espèce dans pokeplatinum ; tables JSON agrégées dans pokediamond (Diamant et Perle).
    GEN4 = "gen4"


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
HOENN = Region("HOENN", "LITTLEROOT_TOWN", 997)
# Kanto de Rouge Feu et Vert Feuille : d'autres cartes que celles de Rouge, Bleu et Jaune, donc un autre numéro.
FIRERED_KANTO = Region("KANTO", "PALLET_TOWN", 996)
# Les Îles Sevii forment sept ensembles non reliés, placés par map_anchors.csv autour de l'Île 1.
SEVII = Region("SEVII", "ONE_ISLAND", 995)
SINNOH = Region("SINNOH", "TWINLEAF_TOWN", 994)


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
    # Le jeu débloque le Pokédex National après son Pokédex régional (dès la 3e génération) ; PokéAPI ne relie ces jeux
    # qu'à leur Pokédex régional.
    national_dex: bool = False
    # Génération des jeux originaux, pour la ligne des remakes dans le choix du jeu.
    remake_generation: int | None = None


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
# 3e génération : Hoenn et les remakes de Kanto partagent le moteur (docs/generations/generation-3.md).
RUBY_SAPPHIRE = Game(
    "ruby-sapphire",
    "pokeruby",
    (("ruby", "RUBY"), ("sapphire", "SAPPHIRE")),
    "ruby-sapphire-emerald",
    (VersionCover("ruby", "groudon", 0xA8243A), VersionCover("sapphire", "kyogre", 0x2F4FB0)),
    PretFormat.GEN3,
    (HOENN,),
    national_dex=True,
)

EMERALD = Game(
    "emerald",
    "pokeemerald",
    (("emerald", "EMERALD"),),
    "ruby-sapphire-emerald",
    (VersionCover("emerald", "rayquaza", 0x2E9A5A),),
    PretFormat.GEN3,
    (HOENN,),
    national_dex=True,
)

FIRERED_LEAFGREEN = Game(
    "firered-leafgreen",
    "pokefirered",
    (("firered", "FIRERED"), ("leafgreen", "LEAFGREEN")),
    "firered-leafgreen",
    (VersionCover("firered", "charizard", 0xE8642A), VersionCover("leafgreen", "venusaur", 0x6DB33F)),
    PretFormat.GEN3,
    (FIRERED_KANTO, SEVII),
    national_dex=True,
    remake_generation=1,
)
GEN3_GAMES: tuple[Game, ...] = (RUBY_SAPPHIRE, EMERALD, FIRERED_LEAFGREEN)
PLATINUM = Game(
    "platinum",
    "pokeplatinum",
    (("platinum", "PLATINUM"),),
    "platinum",
    (VersionCover("platinum", "giratina", 0xA49A72),),
    PretFormat.GEN4,
    (SINNOH,),
    national_dex=True,
)
DIAMOND_PEARL = Game(
    "diamond-pearl",
    "pokediamond",
    (("diamond", "DIAMOND"), ("pearl", "PEARL")),
    "diamond-pearl",
    (VersionCover("diamond", "dialga", 0x7D9DC4), VersionCover("pearl", "palkia", 0xCF9EB5)),
    PretFormat.GEN4,
    (SINNOH,),
    national_dex=True,
)
GEN4_GAMES: tuple[Game, ...] = (PLATINUM, DIAMOND_PEARL)
GAMES: tuple[Game, ...] = (*_GEN1_GAMES, GOLD_SILVER, CRYSTAL, *GEN3_GAMES, *GEN4_GAMES)
GAMES_IN_PROGRESS: tuple[Game, ...] = ()
# Tous les jeux générés : ceux de l'application, puis ceux en cours d'intégration.
ALL_GAMES: tuple[Game, ...] = (*GAMES, *GAMES_IN_PROGRESS)
# Tous les jeux déclarés, générés ou non. La famille de cartes d'un jeu est aussi sa branche, que les contrôles
# d'obtention traitent comme une génération à part (validate._check_obtainable).
DECLARED_GAMES: tuple[Game, ...] = tuple(dict.fromkeys((*ALL_GAMES, *GEN3_GAMES, *GEN4_GAMES)))


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


# Méthodes de rencontre « uniques » (un Pokémon donné, fixe, échangé, errant ou caché) : pas de probabilité,
# on compte le nombre d'exemplaires. Toutes les autres sont des rencontres aléatoires dont
# les probabilités (rarity) d'une zone totalisent 100 %.
# La pêche de Barpau en fait partie : 50 % sur six cases de la Route 119 tirées au hasard, en plus de la table de la
# route ; elle ne complète aucune table et ne se place sur aucune case fixe.
ONE_OFF_METHODS = frozenset(
    {
        "gift",
        "gift-egg",
        "static",
        "pokeflute",
        "npc-trade",
        "squirt-bottle",
        "roaming-grass",
        "roaming-water",
        "devon-scope",
        "wailmer-pail",
        "feebas-tile-fishing",
        "colosseum-bonus-disc-jpn",
        "colosseum-bonus-disc-us",
        "pokemon-channel-pal",
        "pokemon-ranger",
    }
)
# Événements externes : un autre jeu ou une distribution donne le Pokémon (méthodes), ou le billet qui ouvre le lieu
# (lieux PokéAPI : Roc Nombri, Île Aurore, Île Lointaine, Île du Sud). Ces rencontres sont gardées avec la
# mention EXTERNAL_EVENT_NOTE, mais ne rendent pas le Pokémon obtenable dans le jeu (validate._check_obtainable).
EXTERNAL_EVENT_METHODS = frozenset(
    {"colosseum-bonus-disc-jpn", "colosseum-bonus-disc-us", "pokemon-channel-pal", "pokemon-ranger"}
)
EXTERNAL_EVENT_LOCATIONS = event_locations() | frozenset(
    {"pal-park", "newmoon-island", "flower-paradise", "sinnoh-hall-of-origin-1", "sinnoh-hall-of-origin-2"}
)
# Métamo : seule la table A (Nosferapti) est accessible sans distribution externe ; les tables B à I
# étaient prévues pour le Cadeau Mystère, jamais distribué. Garder les rencontres, sans les compter.
EXTERNAL_EVENT_AREAS = frozenset(
    f"{location}/{table}" for location in ("kanto-altering-cave", "hoenn-altering-cave") for table in "bcdefghi"
)
EXTERNAL_EVENT_NOTE = "Événement externe"
