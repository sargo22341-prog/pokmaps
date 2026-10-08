"""Terrains où le jeu fait apparaître des Pokémon sauvages, lus dans les sources pret de la génération."""

from __future__ import annotations

from pathlib import Path

from pokemaps_data.games import ALL_GAMES
from pokemaps_data.maps_layout import GameMaps, identifier, read_layout_curation
from pokemaps_data.pret_reader import open_pret
from pokemaps_data.sources import pret_dir

from .catalog import Family


class WildTerrains:
    """Terrains de chaque lieu (herbes, sol, eau, arbres, rochers) : l'éditeur ne propose que ceux où un Pokémon peut
    apparaître. Chaque jeu est lu avec le lecteur de son format pret (open_pret).

    Les sources pret doivent déjà être dans le cache (python tools/build_data.py) : l'éditeur ne télécharge rien."""

    def __init__(self, cache: Path) -> None:
        self.cache = cache
        self._games: dict[str, tuple[GameMaps, dict[str, str]]] = {}

    def kinds(self, family: Family, map_identifier: str) -> frozenset[str]:
        """Terrains du lieu dans au moins un jeu de la famille (les plans sont communs à la famille)."""
        found: set[str] = set()
        for version_group in family.version_groups:
            game_maps, consts = self._game(version_group)
            if map_identifier in consts:
                found |= game_maps.wild_terrains(consts[map_identifier])
        return frozenset(found)

    def region(self, family: Family, map_identifier: str) -> str | None:
        """Carte du monde (identifiant, ex. « johto ») de la région du lieu, d'après le premier jeu de la famille qui
        le contient : la sienne pour une ville ou une route, celle de la ville ou route d'où l'on y entre sinon."""
        for version_group in family.version_groups:
            game_maps, consts = self._game(version_group)
            if map_identifier in consts:
                const = consts[map_identifier]
                return identifier(game_maps.world_region[game_maps.parents.get(const, const)])
        return None

    def _game(self, version_group: str) -> tuple[GameMaps, dict[str, str]]:
        if version_group not in self._games:
            game = next(game for game in ALL_GAMES if game.version_group == version_group)
            root = pret_dir(self.cache, game.pret_repo)
            if not (root / ".complete").is_file():
                raise FileNotFoundError(f"Sources pret absentes : lancer d'abord python tools/build_data.py ({root})")
            game_maps = GameMaps(open_pret(game, root), game, read_layout_curation())
            self._games[version_group] = (game_maps, {identifier(const): const for const in game_maps.placements})
        return self._games[version_group]
