"""Valide les assets versionnés sans téléchargement ni génération."""

import argparse
import sqlite3
import sys
from pathlib import Path

from pokemaps_data.asset_manifest import check_manifest
from pokemaps_data.validate import validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=Path(__file__).resolve().parent.parent / "app/src/main/assets")
    args = parser.parse_args()
    try:
        check_manifest(args.assets)
        errors = validate(args.assets / "database/pokedex.db")
        if errors:
            raise ValueError("Base incohérente :\n" + "\n".join(errors))
    except (OSError, ValueError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("OK : assets versionnés complets, empreintes et base cohérentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
