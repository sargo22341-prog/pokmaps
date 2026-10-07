"""Lecteur pret d'un jeu, choisi d'après le format de ses sources (games.Game.pret_format)."""

from __future__ import annotations

from pathlib import Path

from .games import Game, PretFormat
from .pret import PretRepo
from .pret_gen2 import Gen2PretRepo

PretReader = PretRepo | Gen2PretRepo


def open_pret(game: Game, root: Path) -> PretReader:
    """Lecteur des sources pret du jeu, extraites dans `root`."""
    match game.pret_format:
        case PretFormat.GEN1:
            return PretRepo(root)
        case PretFormat.GEN2:
            return Gen2PretRepo(root, game.pret_versions)
