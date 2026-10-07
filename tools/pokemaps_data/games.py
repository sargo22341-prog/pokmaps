"""Jeux pris en charge par l'application.

Ajouter un jeu (ex. Or/Argent) revient à ajouter une entrée ici : toutes les données
(Pokémon, attaques, rencontres, lieux…) sont ensuite extraites de PokéAPI pour ce groupe
de versions. Les identifiants sont ceux de PokéAPI (table version_groups).
Les cartes sont générées depuis le désassemblage pret du jeu (le lecteur de pret.py est
écrit pour la 1re génération : un autre jeu demandera d'adapter la lecture de ses cartes).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Game:
    # Identifiant PokéAPI du groupe de versions (ex. "red-blue").
    version_group: str
    # Désassemblage pret d'où sont générées les cartes (cf. sources.PRET_COMMITS).
    pret_repo: str
    # Versions PokéAPI du jeu et symbole qui les distingue dans pret (IF DEF(_RED) : propre à Rouge).
    pret_versions: tuple[tuple[str, str], ...]


GAMES: tuple[Game, ...] = (
    Game("red-blue", "pokered", (("red", "_RED"), ("blue", "_BLUE"))),
    Game("yellow", "pokeyellow", (("yellow", "_YELLOW"),)),
)

# Méthodes de rencontre « uniques » (un Pokémon donné, fixe ou échangé) : pas de probabilité,
# on compte le nombre d'exemplaires. Toutes les autres sont des rencontres aléatoires dont
# les probabilités (rarity) d'une zone totalisent 100 %.
ONE_OFF_METHODS = frozenset({"gift", "gift-egg", "static", "pokeflute", "npc-trade"})
