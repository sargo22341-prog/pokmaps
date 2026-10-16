"""Terrains sauvages des cartes DS : cases où le moteur déclenche une rencontre, et leur centre sur l'image oblique.

Le moteur lit le comportement de la case sous le joueur (GetTileEncounterRateAndType) : une case à drapeau de
rencontre déclenche la marche, ou le surf si elle est aussi surfable ; la pêche vise une case surfable. Les herbes
(hautes, très hautes, boue herbeuse) sont distinguées du sol des grottes ; les arbres à Miel sont l'objet posé de
leur modèle. Seules les cases sans collision comptent pour la marche.

Une case porte une hauteur par surface praticable (BDHC) : son centre est projeté comme le rendu oblique de la
phase 3 (sol exact à 16 px par case, un point de hauteur h remonte de h × cot(élévation)). Les cases à plusieurs
niveaux (ponts, passerelles) gardent leur terrain mais n'accueillent pas d'emplacement, qui masquerait le niveau
supérieur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_land import BLOCK_TILES, FX_ONE, heights
from .pret_gen4_map_models import EMPTY_BLOCK

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_land import LandBlock
    from .pret_gen4_map_models import Gen4Header
    from .pret_gen4_wild_rules import TileRules, WildRules

STEP_PX = 16
BLOCK_PX = BLOCK_TILES * STEP_PX
# Deux surfaces séparées d'au moins une case sont deux niveaux (comme maps_levels_gen4).
_LEVEL_GAP = STEP_PX * FX_ONE
_WATER_METHODS = frozenset({"surf", "old-rod", "good-rod", "super-rod"})

Cell = tuple[int, int]


@dataclass(frozen=True)
class BlockView:
    """Bloc d'un assemblage : position dans la matrice, altitude et cotangente de sa caméra (fx32)."""

    column: int
    row: int
    altitude: int
    cotangent: int


@dataclass(frozen=True)
class HeaderTerrain:
    cells: dict[str, tuple[Cell, ...]]  # terrain -> cases globales de la matrice
    single_level: frozenset[Cell]  # cases à une seule surface, où un emplacement ne masque rien
    heights: dict[Cell, int]  # hauteur (fx32) de la surface de chaque case de terrain


def header_blocks(repo: Gen4PretRepo, header: Gen4Header) -> list[tuple[int, int, int]]:
    """Blocs (colonne, ligne, numéro) de la matrice qui appartiennent à l'en-tête."""
    matrix = repo.matrices[header.matrix]
    return [
        (column, row, block)
        for row, line in enumerate(matrix.blocks)
        for column, block in enumerate(line)
        if block != EMPTY_BLOCK and (matrix.headers is None or matrix.headers[row][column] == header.index)
    ]


def has_tall_grass(repo: Gen4PretRepo, header: Gen4Header, rules: WildRules) -> bool:
    """Le Pokéradar ne s'utilise que debout dans les hautes herbes (CanUsePokeRadar)."""
    tall = rules.tiles.tall_grass
    for _, _, number in header_blocks(repo, header):
        block = repo.land_block(number)
        if any(
            block.behavior(x, z) == tall and not block.collision(x, z)
            for z in range(BLOCK_TILES)
            for x in range(BLOCK_TILES)
        ):
            return True
    return False


def header_terrain(repo: Gen4PretRepo, header: Gen4Header, rules: WildRules, methods: frozenset[str]) -> HeaderTerrain:
    """Cases de chaque terrain où l'une des `methods` de l'en-tête fait apparaître un Pokémon."""
    matrix = repo.matrices[header.matrix]
    cells: dict[str, list[Cell]] = {"grass": [], "floor": [], "water": [], "tree": []}
    levels: dict[Cell, tuple[int, ...]] = {}
    for column, row, number in header_blocks(repo, header):
        block = repo.land_block(number)
        altitude = (matrix.altitudes[row][column] if matrix.altitudes else 0) * 8 * FX_ONE
        found = [
            (kind, (x, z))
            for z in range(BLOCK_TILES)
            for x in range(BLOCK_TILES)
            if (kind := _kind(block.behavior(x, z), block.collision(x, z), rules.tiles, methods))
        ]
        if "honey-tree" in methods:
            found.extend(("tree", cell) for cell in _honey_trees(block, rules.honey.model))
        for kind, (x, z) in found:
            surfaces = _surfaces(block, x, z)
            if surfaces:
                cell = (column * BLOCK_TILES + x, row * BLOCK_TILES + z)
                cells[kind].append(cell)
                levels[cell] = tuple(value + altitude for value in surfaces)
    single = frozenset(cell for cell, values in levels.items() if values[-1] - values[0] < _LEVEL_GAP)
    top = {cell: values[-1] for cell, values in levels.items()}
    return HeaderTerrain({kind: tuple(found) for kind, found in cells.items() if found}, single, top)


def _surfaces(block: LandBlock, x: int, z: int) -> tuple[int, ...]:
    if block.bdhc is None:
        return ()
    return heights(block.bdhc, (x * STEP_PX - 248) * FX_ONE, (z * STEP_PX - 248) * FX_ONE)


def _kind(behavior: int, collision: bool, tiles: TileRules, methods: frozenset[str]) -> str | None:
    encounter = behavior in tiles.encounter
    if behavior in tiles.surfable:
        fishing = bool(methods & (_WATER_METHODS - {"surf"}))
        return "water" if ("surf" in methods and encounter) or fishing else None
    if not encounter or collision or "walk" not in methods:
        return None
    return "grass" if behavior in tiles.grass else "floor"


def _honey_trees(block: LandBlock, model: int) -> list[Cell]:
    """Case de chaque arbre à Miel du bloc (position de l'objet posé, relative au centre du bloc)."""
    return [
        (
            (prop.position[0] // FX_ONE + BLOCK_PX // 2) // STEP_PX,
            (prop.position[2] // FX_ONE + BLOCK_PX // 2) // STEP_PX,
        )
        for prop in block.props
        if prop.model == model
    ]


def cell_point(cell: Cell, height: int, view: BlockView, bounds: tuple[int, int, int, int]) -> tuple[int, int]:
    """Centre de la case sur l'image de l'assemblage dont `bounds` est le cadre (pixels de la matrice)."""
    x, z = cell
    local_x, local_z = x - view.column * BLOCK_TILES, z - view.row * BLOCK_TILES
    pixel_x = local_x * STEP_PX + STEP_PX // 2 + view.column * BLOCK_PX
    ground = (local_z * STEP_PX + STEP_PX // 2) * FX_ONE - height * view.cotangent // FX_ONE
    return pixel_x - bounds[0], ground // FX_ONE + view.row * BLOCK_PX - bounds[1]
