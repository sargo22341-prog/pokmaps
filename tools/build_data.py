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
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

# Lancé en script (`python tools/build_data.py`), Python place déjà tools/ en tête de sys.path.
from pokemaps_data.achievement_resources import build_achievement_resources
from pokemaps_data.asset_manifest import write_manifest
from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.encounter_backgrounds import build_encounter_backgrounds
from pokemaps_data.games import ALL_GAMES, FIRERED_LEAFGREEN, GAMES, GAMES_IN_PROGRESS, Game
from pokemaps_data.hoenn_catalog import build_hoenn_catalog
from pokemaps_data.maps import build_maps
from pokemaps_data.maps_gen3 import GEN3_MAP_GAMES, HOENN_MAP_GAMES, build_gen3_maps, validate_catalog
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_gen3_fixed import build_fixed_catalog
from pokemaps_data.preview_curation_gen3 import build_curation_preview
from pokemaps_data.preview_wild_gen3 import build_wild_preview
from pokemaps_data.sinnoh_catalog import build_sinnoh_catalog
from pokemaps_data.sources import PRET_COMMITS, PREVIEW_DIR, fetch_pokeapi_csv, fetch_pret
from pokemaps_data.sprites import build_sprites
from pokemaps_data.validate import validate
from pokemaps_data.validate_hoenn_character_state import validate_hoenn_characters

ROOT = Path(__file__).resolve().parent
DEFAULT_ASSETS = ROOT.parent / "app/src/main/assets"


def _output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS, help="dossier des assets de l'application")
    parser.add_argument("--preview", type=Path, default=PREVIEW_DIR, help="dossier de l'aperçu de tous les jeux")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache", help="dossier de cache des sources")
    parser.add_argument(
        "--application-only", action="store_true", help="générer les jeux actifs sans aperçu supplémentaire"
    )
    parser.add_argument(
        "--reuse-gen3-maps", action="store_true", help="réutiliser les cartes GBA existantes et validées"
    )
    parser.add_argument("--map-workers", type=int, choices=range(1, 9), default=4, help="processus de rendu DS (1 à 8)")


def _preparatory_arguments(maps_only: argparse._MutuallyExclusiveGroup) -> None:
    maps_only.add_argument(
        "--hgss-encounters-only", action="store_true", help="valider les rencontres HGSS après l'aperçu des cartes"
    )
    maps_only.add_argument(
        "--hgss-pokemon-only", action="store_true", help="valider les Pokémon HGSS sans cartes ni activation Android"
    )
    maps_only.add_argument(
        "--hgss-maps-only", action="store_true", help="générer la preuve HGSS et le catalogue Johto qualifié, sans ROM"
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _output_arguments(parser)
    maps_only = parser.add_mutually_exclusive_group()
    _preparatory_arguments(maps_only)
    maps_only.add_argument(
        "--encounter-backgrounds-only",
        action="store_true",
        help="exporter les décors fixes des rencontres depuis Émeraude",
    )
    maps_only.add_argument(
        "--sinnoh-maps-only", action="store_true", help="générer les cartes DS sans activation Android"
    )
    maps_only.add_argument(
        "--sinnoh-catalogs-only", action="store_true", help="réexporter les catalogues DS sans refaire les tuiles"
    )
    maps_only.add_argument(
        "--sinnoh-scenes-only", action="store_true", help="réexporter le décor moteur et les niveaux DS existants"
    )
    maps_only.add_argument("--sinnoh-pokemon-only", action="store_true", help="générer l'aperçu Pokémon DS sans cartes")
    maps_only.add_argument(
        "--sinnoh-encounters-only",
        action="store_true",
        help="générer l'aperçu des rencontres et emplacements DS (après --sinnoh-maps-only)",
    )
    maps_only.add_argument(
        "--sinnoh-characters-only",
        action="store_true",
        help="générer l'aperçu des dresseurs, combats, objets et du Pokédex National DS",
    )
    maps_only.add_argument("--hoenn-content-only", action="store_true", help="exporter baies, concours et décorations")
    maps_only.add_argument("--sinnoh-content-only", action="store_true", help="exporter les contenus propres à Sinnoh")
    maps_only.add_argument(
        "--achievement-resources-only", action="store_true", help="générer les ressources de succès depuis les archives"
    )
    maps_only.add_argument(
        "--remake-fixed-only", action="store_true", help="exporter les Pokémon fixes Rouge Feu/Vert Feuille"
    )
    maps_only.add_argument("--hoenn-fixed-only", action="store_true", help="exporter les Pokémon fixes de Hoenn")
    maps_only.add_argument(
        "--hoenn-maps-only", action="store_true", help="régénérer seulement les cartes Hoenn préparatoires"
    )
    maps_only.add_argument(
        "--remake-maps-only", action="store_true", help="régénérer seulement les cartes Rouge Feu/Vert Feuille"
    )
    maps_only.add_argument(
        "--gen3-encounters-only",
        action="store_true",
        help="générer l'aperçu PC des rencontres GBA, sans personnages ni activation Android",
    )
    maps_only.add_argument(
        "--gen3-items-only", action="store_true", help="générer l'aperçu GBA avec les objets au sol et cachés"
    )
    maps_only.add_argument(
        "--gen3-trainers-only", action="store_true", help="générer l'aperçu GBA et le catalogue complet des dresseurs"
    )
    maps_only.add_argument(
        "--gen3-curation-only", action="store_true", help="valider et exporter les corrections des personnages GBA"
    )
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.encounter_backgrounds_only:
        build_encounter_backgrounds(args.cache, args.assets)
        write_manifest(args.assets)
        return 0
    if _hgss_preview(args) or _sinnoh_preview(args):
        return 0
    if args.achievement_resources_only:
        build_achievement_resources(Path(__file__).resolve().parents[1] / "app/src/main/res/values")
        return 0
    if args.hoenn_content_only:
        build_hoenn_catalog(args.cache, args.assets)
        write_manifest(args.assets)
        return 0
    if args.sinnoh_content_only:
        build_sinnoh_catalog(args.cache, args.assets)
        write_manifest(args.assets)
        return 0
    if args.hoenn_fixed_only or args.remake_fixed_only:
        group = "firered-leafgreen" if args.remake_fixed_only else "hoenn"
        build_fixed_catalog(args.cache, args.assets, group)
        write_manifest(args.assets)
        return 0
    if args.gen3_curation_only:
        build_curation_preview(args.cache, args.preview)
        return 0
    if args.gen3_encounters_only or args.gen3_items_only or args.gen3_trainers_only:
        build_wild_preview(
            args.cache,
            args.assets,
            args.preview,
            include_items=args.gen3_items_only or args.gen3_trainers_only,
            include_trainers=args.gen3_trainers_only,
        )
        return 0
    if args.hoenn_maps_only or args.remake_maps_only:
        games = HOENN_MAP_GAMES if args.hoenn_maps_only else (FIRERED_LEAFGREEN,)
        build_gen3_maps(args.cache, args.assets / "maps", games)
        _map_catalogs(args.cache, args.assets, games)
        if args.hoenn_maps_only:
            build_hoenn_catalog(args.cache, args.assets)
        write_manifest(args.assets)
        return 0

    return _build_all(args)


def _sinnoh_preview(args: argparse.Namespace) -> bool:
    """Aperçus DS demandés (cartes, décor, catalogues, Pokémon, rencontres, personnages) ; faux si aucun ne l'est."""
    if args.sinnoh_scenes_only:
        from pokemaps_data.maps_scenes_gen4 import rebuild_scenes

        rebuild_scenes(args.cache, args.preview / "sinnoh-maps", args.map_workers)
    elif args.sinnoh_catalogs_only:
        from pokemaps_data.maps_refresh_gen4 import refresh_catalogs

        refresh_catalogs(args.cache, args.preview / "sinnoh-maps")
    elif args.sinnoh_maps_only:
        from pokemaps_data.maps_gen4 import build_gen4_maps

        build_gen4_maps(args.cache, args.preview / "sinnoh-maps", args.map_workers)
    elif args.sinnoh_encounters_only:
        from pokemaps_data.preview_wild_gen4 import build_wild_preview_gen4

        build_wild_preview_gen4(args.cache, args.preview, args.assets)
    elif args.sinnoh_characters_only:
        from pokemaps_data.preview_characters_gen4 import build_characters_preview_gen4

        build_characters_preview_gen4(args.cache, args.preview)
    elif args.sinnoh_pokemon_only:
        from pokemaps_data.preview_pokemon_gen4 import build_pokemon_preview

        build_pokemon_preview(args.cache, args.preview, args.assets)
    else:
        return False
    return True


def _hgss_preview(args: argparse.Namespace) -> bool:
    if args.hgss_encounters_only:
        from pokemaps_data.preview_wild_hgss import build_hgss_encounters

        build_hgss_encounters(args.cache, args.preview, args.assets)
        return True
    if args.hgss_pokemon_only:
        from pokemaps_data.preview_pokemon_hgss import build_hgss_pokemon

        build_hgss_pokemon(args.cache, args.preview, args.assets)
        return True
    if not args.hgss_maps_only:
        return False
    from pokemaps_data.preview_maps_hgss import build_hgss_maps

    build_hgss_maps(args.cache, args.preview, args.map_workers)
    return True


def _build_all(args: argparse.Namespace) -> int:
    # Tous les dépôts épinglés, y compris ceux des jeux en cours d'intégration : les tests les lisent dans le cache.
    print(f"Téléchargement des désassemblages pret ({', '.join(PRET_COMMITS)})…")
    repos = {repo: fetch_pret(args.cache, repo) for repo in PRET_COMMITS}
    print("Téléchargement des CSV PokéAPI…")
    api = PokeApi(fetch_pokeapi_csv(args.cache))

    if args.reuse_gen3_maps:
        for game in GEN3_MAP_GAMES:
            validate_catalog(args.assets / "maps" / game.version_group)
    else:
        build_gen3_maps(args.cache, args.assets / "maps")
    build_fixed_catalog(args.cache, args.assets)

    print(f"Données de l'application ({', '.join(game.version_group for game in GAMES)}) : {args.assets}")
    if not _build(api, args.cache, repos, args.assets, GAMES):
        return 1
    build_hoenn_catalog(args.cache, args.assets)
    build_sinnoh_catalog(args.cache, args.assets)
    build_encounter_backgrounds(args.cache, args.assets)
    if args.assets.resolve() == DEFAULT_ASSETS.resolve():
        build_achievement_resources(Path(__file__).resolve().parents[1] / "app/src/main/res/values")
    if args.assets.resolve() != DEFAULT_ASSETS.resolve():
        shutil.copytree(DEFAULT_ASSETS / "licenses", args.assets / "licenses", dirs_exist_ok=True)
    write_manifest(args.assets)
    if GAMES_IN_PROGRESS and not args.application_only:
        names = ", ".join(game.version_group for game in GAMES_IN_PROGRESS)
        print(f"Aperçu avec les jeux en cours d'intégration ({names}) : {args.preview}")
        if not _build(api, args.cache, repos, args.preview, ALL_GAMES):
            return 1
    return 0


def _map_catalogs(cache: Path, assets: Path, games: tuple[Game, ...]) -> None:
    # Le rendu remplace le dossier : recréer les catalogues indépendants avec les mêmes sources épinglées.
    from pokemaps_data.maps_export_gen3 import export_game

    for game in games:
        if game in GAMES:
            export_game(cache, assets / "maps" / game.version_group, game)
    branch = "firered-leafgreen" if games == (FIRERED_LEAFGREEN,) else "hoenn"
    build_fixed_catalog(cache, assets, branch)


def _build(api: PokeApi, cache: Path, repos: dict[str, Path], assets: Path, games: tuple[Game, ...]) -> bool:
    """Génère cartes, images et base des jeux `games` dans `assets`, puis valide la base."""
    database = assets / "database/pokedex.db"
    print("Génération des cartes…")
    map_data = build_maps(cache, assets / "maps", games, api)

    pret_roots = {game.version_group: repos[game.pret_repo] for game in games}
    builder = DatabaseBuilder(api, games, map_data=map_data, pret_roots=pret_roots)
    from pokemaps_data.preview_encounters_gen4 import complete_preview_encounters

    complete_preview_encounters(builder)
    print("Téléchargement des images (pokesprite, PokeAPI/sprites)…")
    item_sprites = build_sprites(builder, cache, assets / "sprites")

    print("Génération de la base…")
    builder.write(database, item_sprites)

    errors = validate(database)
    if all(game in games for game in HOENN_MAP_GAMES):
        with closing(sqlite3.connect(database)) as connection:
            errors += validate_hoenn_characters(connection)
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
