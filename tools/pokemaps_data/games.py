"""Jeux pris en charge par l'application.

Ajouter un jeu (ex. Or/Argent) revient à ajouter une entrée ici : toutes les données
(Pokémon, attaques, rencontres, lieux…) sont ensuite extraites de PokéAPI pour ce groupe
de versions. Les identifiants sont ceux de PokéAPI (table version_groups).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Game:
    # Identifiant PokéAPI du groupe de versions (ex. "red-blue").
    version_group: str
    # Dossier des sprites du jeu dans PokeAPI/sprites (sprites/pokemon/<dossier>/<numéro>.png).
    sprite_folder: str


GAMES: tuple[Game, ...] = (
    Game("red-blue", "versions/generation-i/red-blue/transparent"),
    Game("yellow", "versions/generation-i/yellow/transparent"),
)

# Méthodes de rencontre « uniques » (un Pokémon donné, fixe ou échangé) : pas de probabilité,
# on compte le nombre d'exemplaires. Toutes les autres sont des rencontres aléatoires dont
# les probabilités (rarity) d'une zone totalisent 100 %.
ONE_OFF_METHODS = frozenset({"gift", "gift-egg", "static", "pokeflute", "npc-trade"})
