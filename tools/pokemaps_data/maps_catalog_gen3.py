"""Lecture des catalogues GBA et assemblage des données de carte communes."""

from __future__ import annotations

import csv
from pathlib import Path

from .games import Game
from .maps import GameMapData, MapRow, SpotRow, WarpRow, read_map_areas, roaming_areas
from .maps_gen3 import validate_catalog
from .maps_items_gen3 import item_rows
from .maps_layout import identifier, read_layout_curation
from .maps_layout_gen3 import Gen3GameMaps
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_items import Gen3MapItem
from .preview_trainers_gen3 import TrainerCatalog, trainer_catalogs


def map_data(
    source: Path,
    root: Path,
    game: Game,
    items: list[Gen3MapItem] | None = None,
    trainers: list[TrainerCatalog] | None = None,
    game_maps: Gen3GameMaps | None = None,
) -> GameMapData:
    validate_catalog(source)
    maps = game_maps or Gen3GameMaps(Gen3PretRepo(root, game.pret_versions), game, read_layout_curation())
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
                row["kind"] or None,
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
        row["version"] or None,
    )
