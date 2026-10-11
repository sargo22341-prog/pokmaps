"""Aperçu PC GBA : rencontres et exports facultatifs des objets fixes, équipes et revanches."""

from __future__ import annotations

import csv
import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path

from .builder import DatabaseBuilder
from .compare_wild_gen3 import compare_wild_tables
from .games import GEN3_GAMES, Game
from .maps import GameMapData, MapRow, SpotRow, WarpRow, read_map_areas, roaming_areas
from .maps_gen3 import validate_catalog
from .maps_items_gen3 import item_rows
from .maps_layout import identifier, read_layout_curation
from .maps_layout_gen3 import Gen3GameMaps
from .pokeapi import PokeApi
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_items import Gen3MapItem
from .preview_items_gen3 import write_item_metadata
from .preview_trainers_gen3 import TrainerCatalog, trainer_catalogs, write_trainer_catalogs
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
        game.version_group: _map_data(
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


def _map_data(
    source: Path,
    root: Path,
    game: Game,
    items: list[Gen3MapItem] | None = None,
    trainers: list[TrainerCatalog] | None = None,
) -> GameMapData:
    validate_catalog(source)
    repo = Gen3PretRepo(root, game.pret_versions)
    maps = Gen3GameMaps(repo, game, read_layout_curation())
    with (source / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        rows = [_map_row(row) for row in csv.DictReader(handle, delimiter="\t")]
    for row in rows:
        if row.is_world and not row.start:
            row.start = next(const for const, region in maps.world_region.items() if region == row.const)
    with (source / "warps.tsv").open(encoding="utf-8", newline="") as handle:
        warps = [
            WarpRow(
                row["map_const"],
                int(row["x"]),
                int(row["y"]),
                row["target"] or None,
                int(row["target_x"]) if row["target_x"] else None,
                int(row["target_y"]) if row["target_y"] else None,
            )
            for row in csv.DictReader(handle, delimiter="\t")
        ]
    spots, terrain = [], {}
    for const in maps.placements:
        for kind, cells in maps.free_cells(const).items():
            if cells:
                terrain[(identifier(const), kind)] = frozenset(maps.point(const, x, y) for x, y in cells)
        for kind, cells in maps.spots(const).items():
            spots.extend(SpotRow(const, kind, *maps.point(const, x, y)) for x, y in cells)
    areas = [
        (const, key)
        for const, key in [*read_map_areas(game.version_group)[game.map_family], *roaming_areas(maps)]
        if const in maps.placements
    ]
    objects = []
    if items is not None:
        objects, metadata = item_rows(maps)
        items.extend(metadata)
    if trainers is not None:
        trainers.extend(trainer_catalogs(maps))
    return GameMapData(rows, areas, warps, objects, spots, terrain, characters_complete=False)


def _map_row(row: dict[str, str]) -> MapRow:
    return MapRow(
        row["const"],
        int(row["number"]),
        row["name_fr"],
        row["parent"] or None,
        int(row["x"]),
        int(row["y"]),
        int(row["width"]),
        int(row["height"]),
        int(row["level_count"]),
        row["is_world"] == "True",
        row["origin"] or None,
        row["start"] or None,
    )
