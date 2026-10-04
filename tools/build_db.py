#!/usr/bin/env python3
"""Génère la base pokedex.db embarquée dans l'application.

Usage :
    python tools/build_db.py                     # télécharge les sources figées puis génère la base
    python tools/build_db.py --out /tmp/pokedex.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pokemaps_data.builder import DatabaseBuilder  # noqa: E402
from pokemaps_data.sources import PRET_RED_BLUE, PRET_YELLOW, fetch_git, fetch_pokeapi_csv  # noqa: E402
from pokemaps_data.validate import validate  # noqa: E402

DEFAULT_OUTPUT = ROOT.parent / "app/src/main/assets/database/pokedex.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="chemin de la base générée")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache", help="dossier de cache des sources")
    args = parser.parse_args()

    print("Récupération des sources…")
    pokered = fetch_git(PRET_RED_BLUE, args.cache)
    pokeyellow = fetch_git(PRET_YELLOW, args.cache)
    pokeapi = fetch_pokeapi_csv(args.cache)

    print("Génération de la base…")
    DatabaseBuilder(pokered, pokeyellow, pokeapi).write(args.out)

    errors = validate(args.out)
    if errors:
        print("Base incohérente :", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    connection = sqlite3.connect(args.out)
    tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    for table in tables:
        count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        print(f"  {table:<24} {count:>6} lignes")
    connection.close()
    print(f"OK : {args.out} ({args.out.stat().st_size // 1024} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
