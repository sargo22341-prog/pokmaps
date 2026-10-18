"""Intégration des catalogues DS validés dans les tables communes de l'application."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

from .builder import DatabaseBuilder
from .games import Game
from .maps import GameMapData, WarpRow
from .maps_data_gen4 import Gen4WildMaps
from .maps_terrain_gen4 import STEP_PX, cell_point
from .pokeapi import PokeApi
from .pret_gen4_distortion import map_offsets
from .pret_gen4_land import BLOCK_TILES, FX_ONE, heights
from .preview_characters_gen4 import SCHEMA as CHARACTER_SCHEMA
from .preview_characters_gen4 import character_catalog
from .sources import PRET_COMMITS, PREVIEW_DIR, fetch_pokeapi_csv, fetch_pret
from .story_events import read_story_events
from .validate_maps_gen4 import check_inventory, validate_catalog, write_inventory

if TYPE_CHECKING:
    from .preview_characters_gen4 import CharacterCatalog


class Gen4MapProjection:
    def __init__(self, maps: Gen4WildMaps) -> None:
        self.maps = maps
        self.offsets = map_offsets(maps.repo)

    def point(self, const: str, x: int, z: int, height: int | None = None) -> tuple[int, int]:
        display = self.maps.displays[self.maps.parents[const]]
        header = self.maps.headers[const]
        offset_x, offset_y, offset_z = self.offsets.get(header.index, (0, 0, 0))
        x, z = x - offset_x, z - offset_z
        if height is not None:
            height -= offset_y * STEP_PX * FX_ONE
        key = (x // BLOCK_TILES, z // BLOCK_TILES)
        if key not in display.blocks:
            raise ValueError(f"{const} : position hors des blocs rendus : {x}, {z}")
        view = display.blocks[key]
        if height is None or height == 0:
            matrix = self.maps.repo.matrices[header.matrix]
            block = self.maps.repo.land_block(matrix.blocks[key[1]][key[0]])
            surfaces = (
                ()
                if block.bdhc is None
                else heights(block.bdhc, (x % 32 * STEP_PX - 248) * FX_ONE, (z % 32 * STEP_PX - 248) * FX_ONE)
            )
            height = (max(surfaces) if surfaces else 0) + view.altitude * 8 * FX_ONE
        return cell_point((x, z), height, view, display.bounds)


def export_game(cache: Path, output: Path, game: Game) -> GameMapData:
    source = PREVIEW_DIR / "sinnoh-maps" / game.version_group
    if not source.is_dir():
        from .maps_gen4 import build_gen4_maps

        build_gen4_maps(cache, source.parent)
    check_inventory(source)
    validate_catalog(source)
    metadata = json.loads((source / "matrices.json").read_text(encoding="utf-8"))
    if metadata["commit"] != PRET_COMMITS[game.pret_repo]:
        raise ValueError(f"{source} : cartes DS à régénérer avec les sources épinglées")
    root = fetch_pret(cache, game.pret_repo)
    builder = DatabaseBuilder(PokeApi(fetch_pokeapi_csv(cache)), (game,), pret_roots={game.version_group: root})
    repo = builder.gen4_repo(game, "l'intégration des cartes")
    maps = Gen4WildMaps(source, repo, game, builder.encounters.gen4_contexts[game.version_group])
    data = maps.map_data()
    projection = Gen4MapProjection(maps)
    data.warps = _warps(source, projection)
    story = read_story_events()
    catalog = character_catalog(repo, game, story)
    from .maps_characters_gen4 import character_rows

    data.objects = character_rows(builder, catalog, projection, source)
    from .maps_actor_positions_gen4 import clear_actor_passages, space_trainer_duos

    clear_actor_passages(data, projection)
    space_trainer_duos(data.objects)
    _assign_display_positions(data)
    data.story = story
    data.named_characters = frozenset(catalog.names.characters)
    data.characters_complete = True
    _write_catalog_assets(source, output, catalog)
    return data


def _write_catalog_assets(source: Path, output: Path, catalog: CharacterCatalog) -> None:
    expected = output.parent.resolve() / catalog.version_group
    if output.is_symlink() or output.resolve() != expected or output.resolve() == source.resolve():
        raise ValueError(f"Destination de cartes DS invalide : {output}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output)
    # Git conserve ces métadonnées en LF : leurs empreintes doivent être identiques sur Windows et Linux.
    for path in sorted(output.iterdir()):
        if path.suffix in {".json", ".tsv"}:
            path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    payload = {"schema": CHARACTER_SCHEMA, "families": [asdict(catalog)]}
    (output / "characters.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n"
    )
    write_inventory(output)


def _assign_display_positions(data: GameMapData) -> None:
    maps = {row.const: row for row in data.maps}
    for obj in [*data.objects, *data.warps]:
        row = maps[obj.map_const]
        if row.x <= obj.x <= row.x + row.width and row.y <= obj.y <= row.y + row.height:
            continue
        # Les événements d'un lieu peuvent poser du décor dans une autre partie du même assemblage.
        if row.parent is None:
            raise ValueError(f"{obj.map_const} : objet hors de l'image : {obj}")
        display = maps[row.parent]
        if not (0 <= obj.x <= display.width and 0 <= obj.y <= display.height):
            raise ValueError(f"{obj.map_const} : objet hors de l'assemblage : {obj}")
        obj.map_const = display.const


def _warps(source: Path, projection: Gen4MapProjection) -> list[WarpRow]:
    maps = projection.maps
    constants = {header.index: const for const, header in maps.headers.items()}
    result = []
    with (source / "passages.tsv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for row in rows:
        # Vol et trajets globaux n'ont pas de case de départ ; leur provenance reste dans passages.tsv.
        if row["kind"] == "unused" or not row["source"] or not row["x"] or not row["z"]:
            continue
        const = constants[int(row["source"])]
        target = constants.get(int(row["target"])) if row["target"] else None
        arrival = (
            projection.point(target, int(row["target_x"]), int(row["target_z"]))
            if (target and row["target_x"] and row["target_z"])
            else (None, None)
        )
        result.append(WarpRow(const, *projection.point(const, int(row["x"]), int(row["z"])), target, *arrival))
    return list({(w.map_const, w.x, w.y, w.target, w.target_x, w.target_y): w for w in result}.values())
