"""Données de carte DS pour la base : catalogue de l'aperçu des cartes (phase 3), zones et emplacements sauvages.

Les cartes, plans et assemblages viennent de catalog.tsv et matrices.json, produits et validés avec les tuiles. Les
emplacements des Pokémon sauvages sont tirés sur les cases de chaque terrain (maps_terrain_gen4) qui n'ont qu'un
niveau et qu'aucun personnage ni passage n'occupe ; leur centre est projeté sur l'image oblique de l'assemblage.
Les passages et personnages DS entrent dans la base avec l'activation de l'application (phases 5 et 6).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .map_spots import SPOT_KINDS
from .maps import GameMapData, MapRow, SpotRow, read_map_areas
from .maps_layout import SPOTS_PER_KIND, identifier, spread
from .maps_terrain_gen4 import BLOCK_PX, STEP_PX, BlockView, cell_point, header_terrain
from .pret_gen4_wild import wild_tables

if TYPE_CHECKING:
    from .games import Game
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header
    from .pret_gen4_wild import WildContext

ROAMING_AREA = "roaming-sinnoh/area"
Cell = tuple[int, int]


@dataclass(frozen=True)
class Display:
    const: str
    bounds: tuple[int, int, int, int]
    blocks: dict[tuple[int, int], BlockView]


class Gen4WildMaps:
    """Terrains sauvages et emplacements des en-têtes DS d'un catalogue, avec l'interface de l'éditeur : cases
    libres de chaque terrain et leur centre en pixels de la carte affichée."""

    def __init__(self, catalog: Path, repo: Gen4PretRepo, game: Game, context: WildContext) -> None:
        self.repo = repo
        self.game = game
        self.context = context
        with (catalog / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
            self.rows = [_map_row(row) for row in csv.DictReader(handle, delimiter="\t")]
        for row in self.rows:
            if row.is_world and not row.start:
                row.start = _start_map(row.const, game, self.rows)
        self.by_const = {row.const: row for row in self.rows}
        self.parents = {row.const: row.parent or row.const for row in self.rows}
        self.world_region = {row.const: "SINNOH" for row in self.rows}
        self.headers = {header.constant: header for header in repo.headers.values() if header.constant in self.parents}
        self.displays = _displays(catalog)
        self.methods = self._methods()
        self._terrain: dict[str, tuple[dict[str, list[Cell]], dict[Cell, tuple[int, int]]]] = {}

    @property
    def placements(self) -> dict[str, str]:
        """En-têtes ayant des rencontres sauvages -> carte affichée."""
        return {const: self.parents[const] for const in self.methods}

    def wild_terrains(self, const: str) -> frozenset[str]:
        return frozenset(kind for kind, cells in self.free_cells(const).items() if cells)

    def free_cells(self, const: str) -> dict[str, list[Cell]]:
        return self._header(const)[0]

    def point(self, const: str, x: int, y: int) -> tuple[int, int]:
        return self._header(const)[1][(x, y)]

    def spots(self, const: str) -> dict[str, list[Cell]]:
        return {
            kind: spread(cells, SPOTS_PER_KIND, f"{const}/{kind}")
            for kind, cells in self.free_cells(const).items()
            if cells
        }

    def map_data(self) -> GameMapData:
        spots, terrain = [], {}
        for const in sorted(self.methods, key=lambda name: self.headers[name].index):
            for kind, cells in self.free_cells(const).items():
                if cells:
                    terrain[(identifier(const), kind)] = frozenset(self.point(const, x, y) for x, y in cells)
            for kind, cells in self.spots(const).items():
                spots.extend(SpotRow(const, kind, *self.point(const, x, y)) for x, y in cells)
        consts = set(self.parents)
        areas = [(const, area) for const, area in read_map_areas(self.game.version_group)[self.game.map_family]]
        areas = [pair for pair in areas if pair[0] in consts]
        routes = {self.repo.headers[index].constant for index in self.context.rules.roamer_headers}
        areas.extend((const, ROAMING_AREA) for const in sorted(routes))
        if missing := sorted(const for const, _ in areas if const not in consts):
            raise ValueError(f"{self.game.version_group} : cartes absentes du catalogue DS : {missing}")
        return GameMapData(self.rows, areas, [], [], spots, terrain, characters_complete=False)

    def _methods(self) -> dict[str, frozenset[str]]:
        found: dict[str, set[str]] = {}
        for version, _ in self.game.pret_versions:
            for table in wild_tables(self.repo, self.context, version):
                const = self.repo.headers[table.header].constant
                if const not in self.parents:
                    raise ValueError(f"{const} : en-tête sauvage absent du catalogue des cartes DS")
                found.setdefault(const, set()).add(table.method)
        return {const: frozenset(methods) for const, methods in found.items()}

    def _header(self, const: str) -> tuple[dict[str, list[Cell]], dict[Cell, tuple[int, int]]]:
        if const not in self._terrain:
            header = self.headers[const]
            terrain = header_terrain(self.repo, header, self.context.rules, self.methods[const])
            display = self.displays[self.parents[const]]
            row = self.by_const[const]
            left, top = (row.x, row.y) if row.parent else (0, 0)
            occupied = _occupied(self.repo, header)
            points = {}
            for cell in terrain.single_level - occupied:
                view = display.blocks[(cell[0] * STEP_PX // BLOCK_PX, cell[1] * STEP_PX // BLOCK_PX)]
                x, y = cell_point(cell, terrain.heights[cell], view, display.bounds)
                # Un point remonté par la hauteur au-delà du bord du lieu n'y serait plus dessiné.
                if left <= x <= left + row.width and top <= y <= top + row.height:
                    points[cell] = (x, y)
            cells = {kind: [cell for cell in terrain.cells.get(kind, ()) if cell in points] for kind in SPOT_KINDS}
            self._terrain[const] = (cells, points)
        return self._terrain[const]


def _start_map(world: str, game: Game, rows: list[MapRow]) -> str:
    """Ville de départ de la région : Bonaugure s'appelle TWINLEAF_TOWN dans Platine et TWINLEAF dans Diamant/Perle."""
    start = next(region.start_map for region in game.regions if region.const == world)
    names = {start, start.removesuffix("_TOWN")}
    found = [
        row.const
        for row in rows
        if row.parent == world and row.const.split("MAP_", 1)[-1].removeprefix("HEADER_") in names
    ]
    if len(found) != 1:
        raise ValueError(f"{game.version_group} : ville de départ de {world} introuvable : {found}")
    return found[0]


def _occupied(repo: Gen4PretRepo, header: Gen4Header) -> frozenset[Cell]:
    """Cases d'un personnage, d'un objet ou d'une entrée, qu'un Pokémon dessiné masquerait."""
    events = repo.events[header.events]
    return frozenset(
        {(obj.x, obj.z) for obj in events.object_events} | {(warp.x, warp.z) for warp in events.warp_events}
    )


def _displays(catalog: Path) -> dict[str, Display]:
    data = json.loads((catalog / "matrices.json").read_text(encoding="utf-8"))
    result = {}
    for display in data["displays"]:
        if display["base"]:
            continue  # Calques inférieurs : les emplacements restent sur la surface visible.
        blocks = {
            (block["offset"][0] // BLOCK_PX, block["offset"][1] // BLOCK_PX): BlockView(
                block["offset"][0] // BLOCK_PX,
                block["offset"][1] // BLOCK_PX,
                block["request"]["altitude"],
                block["request"]["cotangent"],
            )
            for block in display["blocks"]
        }
        result[display["const"]] = Display(display["const"], tuple(display["bounds"]), blocks)
    return result


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
