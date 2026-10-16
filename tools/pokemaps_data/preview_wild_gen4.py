"""Aperçu PC des rencontres DS : base avec cartes, zones, rencontres du moteur et emplacements sauvages.

Il réunit l'aperçu des cartes (--sinnoh-maps-only, phase 3) et les tables du moteur ; l'éditeur des emplacements
l'ouvre avec --assets. Rien n'entre dans les assets de l'application avant l'activation des jeux DS (phase 6).
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, replace
from pathlib import Path

from .asset_manifest import write_manifest
from .builder import DatabaseBuilder
from .builder_maps import build_map_tables
from .compare_wild_gen4 import compare_gen4_tables
from .games import GEN4_GAMES
from .maps import GameMapData
from .maps_data_gen4 import Gen4WildMaps
from .pokeapi import PokeApi
from .preview_pokemon_gen4 import pokemon_preview_tables, validate_pokemon_preview, write_ds_database
from .sources import fetch_pokeapi_csv, fetch_pret
from .sprites import build_sprites

PREVIEW_NAME = "sinnoh-encounters"


def build_wild_preview_gen4(cache: Path, preview: Path, assets: Path) -> None:
    started = time.monotonic()
    target, maps = preview / PREVIEW_NAME, preview / "sinnoh-maps"
    if target.resolve().is_relative_to(assets.resolve()) or assets.resolve().is_relative_to(target.resolve()):
        raise ValueError("L'aperçu des rencontres DS doit être séparé des assets de l'application")
    if not all((maps / game.version_group / "catalog.tsv").is_file() for game in GEN4_GAMES):
        raise FileNotFoundError(f"Cartes DS absentes : lancer d'abord build_data.py --sinnoh-maps-only ({maps})")
    roots = {game.version_group: fetch_pret(cache, game.pret_repo) for game in GEN4_GAMES}
    builder = DatabaseBuilder(PokeApi(fetch_pokeapi_csv(cache)), GEN4_GAMES, pret_roots=roots)
    builder.map_data = {
        game.version_group: Gen4WildMaps(
            maps / game.version_group,
            builder.gen4_repo(game, "les terrains sauvages"),
            game,
            builder.encounters.gen4_contexts[game.version_group],
        ).map_data()
        for game in GEN4_GAMES
    }
    builder.map_data = {group: _used_areas(builder, data) for group, data in builder.map_data.items()}
    target.mkdir(parents=True, exist_ok=True)
    sprites = build_sprites(builder, cache, target / "sprites")
    tables = pokemon_preview_tables(builder, sprites)
    tables["encounter_rate"] = builder.encounters.encounter_rate_table()
    tables.update(build_map_tables(builder))
    write_ds_database(target / "database/pokedex.db", tables, lambda c: validate_pokemon_preview(c, with_maps=True))
    for game in GEN4_GAMES:
        destination = target / "maps" / game.version_group
        shutil.rmtree(destination, ignore_errors=True)
        shutil.copytree(maps / game.version_group, destination)
    shutil.copytree(assets / "licenses", target / "licenses", dirs_exist_ok=True)
    differences = compare_gen4_tables(builder)
    (target / "encounter_comparison.json").write_text(
        json.dumps([asdict(row) for row in differences], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_manifest(target)
    print(f"Comparaison PokéAPI / pret DS : {len(differences)} tables différentes (encounter_comparison.json)")
    print(f"Aperçu des rencontres DS validé : {target} ({time.monotonic() - started:.1f} s)")


def _used_areas(builder: DatabaseBuilder, data: GameMapData) -> GameMapData:
    """Les zones PokéAPI remplacées par le moteur, ou propres à l'autre famille, ne relient plus aucune carte."""
    used, ids = builder.encounters.used_areas, builder.locations.area_ids
    if unknown := sorted({area for _, area in data.areas} - ids.keys()):
        raise ValueError(f"map_areas.csv : zones DS inconnues : {unknown}")
    return replace(data, areas=[(const, area) for const, area in data.areas if ids[area] in used])
