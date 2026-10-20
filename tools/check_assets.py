"""Valide les assets versionnés sans téléchargement ni génération."""

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from pokemaps_data.asset_manifest import check_manifest
from pokemaps_data.encounter_backgrounds import validate_encounter_backgrounds
from pokemaps_data.games import GAMES, GEN3_GAMES, GEN4_GAMES, PretFormat
from pokemaps_data.hoenn_catalog import validate_hoenn_catalog
from pokemaps_data.maps_gen3 import GEN3_MAP_GAMES, validate_catalog
from pokemaps_data.sinnoh_catalog import validate_sinnoh_catalog
from pokemaps_data.validate import validate
from pokemaps_data.validate_gen3_characters import validate_character_catalog
from pokemaps_data.validate_hoenn_character_state import validate_hoenn_characters
from pokemaps_data.validate_maps_gen4 import check_inventory
from pokemaps_data.validate_maps_gen4 import validate_catalog as validate_gen4_catalog
from pokemaps_data.validate_remake_fixed import validate_remake_fixed
from pokemaps_data.validate_team_battles import validate_team_battles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=Path(__file__).resolve().parent.parent / "app/src/main/assets")
    parser.add_argument("--sinnoh-maps", type=Path, help="vérifier aussi les deux catalogues DS préparatoires")
    args = parser.parse_args()
    try:
        check_manifest(args.assets)
        validate_encounter_backgrounds(args.assets)
        validate_hoenn_catalog(args.assets)
        validate_sinnoh_catalog(args.assets)
        validate_remake_fixed(args.assets)
        for game in GEN3_MAP_GAMES:
            validate_catalog(args.assets / "maps" / game.version_group)
        for game in GEN3_GAMES:
            validate_character_catalog(args.assets / "maps" / game.version_group, game)
        for game in GAMES:
            if game.pret_format is PretFormat.GEN4:
                folder = args.assets / "maps" / game.version_group
                check_inventory(folder)
                validate_gen4_catalog(folder)
        errors = validate(args.assets / "database/pokedex.db")
        with closing(sqlite3.connect(args.assets / "database/pokedex.db")) as connection:
            errors += validate_hoenn_characters(connection)
            errors += validate_team_battles(connection)
        if errors:
            raise ValueError("Base incohérente :\n" + "\n".join(errors))
        if args.sinnoh_maps:
            for game in GEN4_GAMES:
                output = args.sinnoh_maps / game.version_group
                check_inventory(output)
                validate_gen4_catalog(output)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        return 1
    print("OK : assets versionnés complets, empreintes et base cohérentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
