#!/usr/bin/env python3
"""Génère les données embarquées dans l'application : la base pokedex.db, les images et les cartes.

Les jeux en cours d'intégration (games.GAMES_IN_PROGRESS) n'entrent pas dans l'application : ils sont générés avec
tous les autres dans un aperçu (--preview), validé de la même façon, que lit l'éditeur des emplacements.

Usage :
    python tools/build_data.py
    python tools/build_data.py --assets /tmp/assets
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Lancé en script (`python tools/build_data.py`), Python place déjà tools/ en tête de sys.path.
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import ALL_GAMES, GAMES, GAMES_IN_PROGRESS, Game
from pokemaps_data.maps import build_maps
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.sources import PRET_COMMITS, PREVIEW_DIR, fetch_pokeapi_csv, fetch_pret
from pokemaps_data.sprites import build_sprites
from pokemaps_data.validate import validate

ROOT = Path(__file__).resolve().parent
DEFAULT_ASSETS = ROOT.parent / "app/src/main/assets"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="dossier des assets de l'application")
    parser.add_argument("--preview", type=Path, default=PREVIEW_DIR, help="dossier de l'aperçu de tous les jeux")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache", help="dossier de cache des sources")
    args = parser.parse_args()

    # Tous les dépôts épinglés, y compris ceux des jeux en cours d'intégration : les tests les lisent dans le cache.
    print(f"Téléchargement des désassemblages pret ({', '.join(PRET_COMMITS)})…")
    repos = {repo: fetch_pret(args.cache, repo) for repo in PRET_COMMITS}
    print("Téléchargement des CSV PokéAPI…")
    api = PokeApi(fetch_pokeapi_csv(args.cache))

    print(f"Données de l'application ({', '.join(game.version_group for game in GAMES)}) : {args.assets}")
    if not _build(api, args.cache, repos, args.assets, GAMES):
        return 1
    if GAMES_IN_PROGRESS:
        names = ", ".join(game.version_group for game in GAMES_IN_PROGRESS)
        print(f"Aperçu avec les jeux en cours d'intégration ({names}) : {args.preview}")
        if not _build(api, args.cache, repos, args.preview, ALL_GAMES):
            return 1
    return 0


def _build(api: PokeApi, cache: Path, repos: dict[str, Path], assets: Path, games: tuple[Game, ...]) -> bool:
    """Génère cartes, images et base des jeux `games` dans `assets`, puis valide la base."""
    database = assets / "database/pokedex.db"
    print("Génération des cartes…")
    map_data = build_maps(cache, assets / "maps", games)

    pret_roots = {game.version_group: repos[game.pret_repo] for game in games}
    builder = DatabaseBuilder(api, games, map_data=map_data, pret_roots=pret_roots)

    print("Téléchargement des images (pokesprite, PokeAPI/sprites)…")
    item_sprites = build_sprites(builder, cache, assets / "sprites")

    print("Génération de la base…")
    builder.write(database, item_sprites)

    errors = validate(database)
    if errors:
        print("Base incohérente :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return False
    _report(database, assets)
    return True


def _report(database: Path, assets: Path) -> None:
    connection = sqlite3.connect(database)
    try:
        tables = [
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        ]
        for table in tables:
            count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"  {table:<26} {count:>6} lignes")
    finally:
        connection.close()
    sprites = sum(1 for _ in (assets / "sprites").rglob("*.*"))
    tiles = list((assets / "maps").rglob("*.webp"))
    tiles_size = sum(tile.stat().st_size for tile in tiles) // 1024
    print(f"OK : {database} ({database.stat().st_size // 1024} Ko), {sprites} images")
    print(f"     {len(tiles)} tuiles de cartes ({tiles_size} Ko)")


if __name__ == "__main__":
    sys.exit(main())
