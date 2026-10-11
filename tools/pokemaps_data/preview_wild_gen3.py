"""Aperçu PC GBA : rencontres et exports facultatifs des objets fixes, équipes et revanches."""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path

from .builder import DatabaseBuilder
from .compare_wild_gen3 import compare_wild_tables
from .games import GEN3_GAMES
from .maps_catalog_gen3 import map_data
from .pokeapi import PokeApi
from .pret_gen3_items import Gen3MapItem
from .preview_items_gen3 import write_item_metadata
from .preview_trainers_gen3 import TrainerCatalog, write_trainer_catalogs
from .sources import fetch_pokeapi_csv, fetch_pret
from .sprites import build_sprites
from .validate import validate


def build_wild_preview(
    cache: Path, assets: Path, output: Path, *, include_items: bool = False, include_trainers: bool = False
) -> None:
    source, target = assets.resolve(), output.resolve()
    if target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("L'aperçu des rencontres doit être séparé des assets de l'application")
    started = time.monotonic()
    roots = {game.version_group: fetch_pret(cache, game.pret_repo) for game in GEN3_GAMES}
    items: list[Gen3MapItem] | None = [] if include_items else None
    trainers: list[TrainerCatalog] | None = [] if include_trainers else None
    data = {
        game.version_group: map_data(
            assets / "maps" / game.version_group, roots[game.version_group], game, items, trainers
        )
        for game in GEN3_GAMES
    }
    builder = DatabaseBuilder(PokeApi(fetch_pokeapi_csv(cache)), GEN3_GAMES, data, roots)
    # Les anciennes tables PokéAPI remplacées ne doivent pas laisser de liens sans rencontre.
    used = builder.encounters.used_areas
    for current in data.values():
        current.areas = [(const, key) for const, key in current.areas if builder.locations.area_ids[key] in used]
    output.mkdir(parents=True, exist_ok=True)
    for game in GEN3_GAMES:
        shutil.copytree(assets / "maps" / game.version_group, output / "maps" / game.version_group, dirs_exist_ok=True)
    sprites = build_sprites(builder, cache, output / "sprites")
    database = output / "database/pokedex.db"
    builder.write(database, sprites)
    errors = validate(database)
    if errors:
        raise ValueError("Aperçu des rencontres GBA incohérent :\n" + "\n".join(errors))
    if items is not None:
        write_item_metadata(database, output / "map_items.json", items)
        print(f"Objets GBA à position fixe : {len(items)} (quantités et drapeaux dans map_items.json)")
    else:
        (output / "map_items.json").unlink(missing_ok=True)
    if trainers is not None:
        write_trainer_catalogs(output / "trainers.json", trainers)
        print(f"Dresseurs GBA : {sum(len(catalog.trainers) for catalog in trainers)} équipes dans trainers.json")
    else:
        (output / "trainers.json").unlink(missing_ok=True)
    differences = compare_wild_tables(builder)
    (output / "encounter_comparison.json").write_text(
        json.dumps([asdict(row) for row in differences], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Comparaison PokéAPI / pret : {len(differences)} tables différentes (encounter_comparison.json)")
    print(f"Aperçu des rencontres GBA validé : {database} ({time.monotonic() - started:.1f} s)")
