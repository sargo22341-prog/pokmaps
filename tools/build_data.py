#!/usr/bin/env python3
"""Génère les données embarquées dans l'application : la base pokedex.db, les images et les cartes.

Usage :
    python tools/build_data.py
    python tools/build_data.py --assets /tmp/assets
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.maps import build_maps  # noqa: E402
from pokemaps_data.pokeapi import PokeApi  # noqa: E402
from pokemaps_data.sources import fetch_pokeapi_csv  # noqa: E402
from pokemaps_data.sprites import build_sprites  # noqa: E402
from pokemaps_data.validate import validate  # noqa: E402

DEFAULT_ASSETS = ROOT.parent / "app/src/main/assets"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="dossier des assets de l'application")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache", help="dossier de cache des sources")
    args = parser.parse_args()
    database = args.assets / "database/pokedex.db"

    print("Génération des cartes (pret/pokered, pret/pokeyellow)…")
    map_data = build_maps(args.cache, args.assets / "maps")

    print("Téléchargement des CSV PokéAPI…")
    builder = DatabaseBuilder(PokeApi(fetch_pokeapi_csv(args.cache)), map_data=map_data)

    print("Téléchargement des images (pokesprite, PokeAPI/sprites)…")
    item_sprites = build_sprites(builder, args.cache, args.assets / "sprites")

    print("Génération de la base…")
    builder.write(database, item_sprites)

    errors = validate(database)
    if errors:
        print("Base incohérente :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    connection = sqlite3.connect(database)
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for table in tables:
        count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table:<26} {count:>6} lignes")
    connection.close()
    sprites = sum(1 for _ in (args.assets / "sprites").rglob("*.png"))
    tiles = list((args.assets / "maps").rglob("*.webp"))
    tiles_size = sum(tile.stat().st_size for tile in tiles) // 1024
    print(f"OK : {database} ({database.stat().st_size // 1024} Ko), {sprites} images")
    print(f"     {len(tiles)} tuiles de cartes ({tiles_size} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
