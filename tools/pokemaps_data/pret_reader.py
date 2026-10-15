"""Lecteur pret d'un jeu, choisi d'après le format de ses sources (games.Game.pret_format)."""

from __future__ import annotations

from pathlib import Path

from .games import Game, PretFormat
from .pret import PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_gen3 import Gen3PretRepo

PretReader = PretRepo | Gen2PretRepo | Gen3PretRepo


def open_pret(game: Game, root: Path) -> PretReader:
    """Lecteur des sources pret du jeu, extraites dans `root`."""
    match game.pret_format:
        case PretFormat.GEN1:
            return PretRepo(root)
        case PretFormat.GEN2:
            return Gen2PretRepo(root, game.pret_versions)
        case PretFormat.GEN3:
            return Gen3PretRepo(root, game.pret_versions)
        case PretFormat.GEN4:
            raise ValueError(f"{game.version_group} : lecteur de cartes DS indisponible ; aperçu Pokémon seulement")
