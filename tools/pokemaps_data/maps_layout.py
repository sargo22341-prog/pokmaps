"""Sélection et placement des cartes d'un jeu pret, et terrain où dessiner les Pokémon sauvages.

Les villes et routes sont placées dans la carte du monde grâce aux connexions entre cartes ; chaque carte
intérieure accessible par les warps est une carte à part, rattachée à la ville ou route d'où l'on y entre.
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from .pret import BLOCK_PX, LAST_MAP, STEP_PX, WATER_TILE, PretRepo

WORLD = "KANTO"
START_MAP = "PALLET_TOWN"

# Emplacements où dessiner les Pokémon sauvages, par carte et par type de terrain (au plus SPOTS_PER_KIND),
# espacés d'au moins SPOT_SPACING cases pour que les sprites ne se chevauchent pas.
SPOTS_PER_KIND = 40
SPOT_SPACING = 3
# Case « intérieure » : au moins autant de voisines (sur 8) du même terrain.
INTERIOR_NEIGHBORS = 7
# Tileset de la forêt de Jade et du Parc Safari : comme dehors, on n'y rencontre des Pokémon qu'en marchant dans
# les herbes (engine/battle/wild_encounters.asm, TryDoWildEncounter).
FOREST_TILESET = "FOREST"

Cell = tuple[int, int]


def identifier(const: str) -> str:
    return const.lower().replace("_", "-")


@dataclass
class Placed:
    """Position d'une carte pret dans la carte affichée qui la contient."""

    display: str  # constante de la carte affichée (WORLD pour les villes et routes)
    x: int  # en pixels
    y: int


def _reachable(cells: list[Cell], starts: set[Cell], blocked: Callable[[Cell, Cell], bool]) -> list[Cell]:
    """Cases accessibles à pied depuis les warps (le bord des grottes est souvent praticable mais isolé)."""
    free = set(cells)
    if not starts:
        return cells
    seen: set[tuple[int, int]] = set()
    queue: deque[Cell] = deque()
    for x, y in starts:
        for neighbor in ((x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbor in free and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    while queue:
        x, y = queue.popleft()
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbor in free and neighbor not in seen and not blocked((x, y), neighbor):
                seen.add(neighbor)
                queue.append(neighbor)
    return [cell for cell in cells if cell in seen]


def spread(cells: list[tuple[int, int]], count: int, seed: str) -> list[tuple[int, int]]:
    """Jusqu'à `count` cases réparties au hasard sur tout le terrain, à `SPOT_SPACING` cases au moins les unes
    des autres.

    Les cases à l'intérieur du terrain (entourées d'herbes, d'eau ou de sol) passent en premier : les Pokémon
    ne sont pas collés aux bords des zones ni de la carte. Le tirage est déterministe (graine = nom de la carte)."""
    free = set(cells)
    rng = random.Random(seed)
    order = sorted(cells)
    rng.shuffle(order)

    def neighbors(cell: tuple[int, int]) -> int:
        x, y = cell
        return sum((x + dx, y + dy) in free for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)

    order.sort(key=lambda c: -min(neighbors(c), INTERIOR_NEIGHBORS))
    chosen: list[tuple[int, int]] = []
    for cell in order:
        if len(chosen) >= count:
            break
        if all((cell[0] - x) ** 2 + (cell[1] - y) ** 2 >= SPOT_SPACING**2 for x, y in chosen):
            chosen.append(cell)
    return chosen


class GameMaps:
    """Cartes d'un jeu : sélection, placement et terrain."""

    def __init__(self, repo: PretRepo) -> None:
        self.repo = repo
        self.maps = repo.maps

    # --- Sélection et placement -------------------------------------------

    @cached_property
    def world_blocks(self) -> dict[str, tuple[int, int]]:
        """Position (en blocs) de chaque ville et route dans la carte du monde, via les connexions."""
        positions = {START_MAP: (0, 0)}
        queue = deque([START_MAP])
        while queue:
            current = self.maps[queue.popleft()]
            x, y = positions[current.const]
            for connection in current.connections:
                target = self.maps[connection.target]
                position = {
                    "north": (x + connection.offset, y - target.height),
                    "south": (x + connection.offset, y + current.height),
                    "west": (x - target.width, y + connection.offset),
                    "east": (x + current.width, y + connection.offset),
                }[connection.direction]
                if target.const not in positions:
                    positions[target.const] = position
                    queue.append(target.const)
                elif positions[target.const] != position:
                    raise ValueError(f"Connexion incohérente {current.const} -> {target.const}")
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        outdoor = {const for const, pret_map in self.maps.items() if pret_map.is_outdoor}
        if outdoor - positions.keys():
            raise ValueError(f"Cartes extérieures non reliées à {START_MAP} : {sorted(outdoor - positions.keys())}")
        return {const: (x - min_x, y - min_y) for const, (x, y) in positions.items()}

    @cached_property
    def world_size(self) -> tuple[int, int]:
        """Taille de la carte du monde, en blocs."""
        width = max(x + self.maps[const].width for const, (x, _) in self.world_blocks.items())
        height = max(y + self.maps[const].height for const, (_, y) in self.world_blocks.items())
        return width, height

    @cached_property
    def indoor_parents(self) -> dict[str, str]:
        """Cartes intérieures accessibles depuis l'extérieur (par les warps) -> ville ou route d'origine."""
        parents: dict[str, str] = {}
        queue: deque[tuple[str, str]] = deque()
        for const in sorted(self.world_blocks, key=lambda c: self.maps[c].number):
            queue.append((const, const))
        while queue:
            const, origin = queue.popleft()
            for warp in self.maps[const].warps:
                target = warp.target
                if target == LAST_MAP or target not in self.maps or self.maps[target].is_outdoor:
                    continue
                if target not in parents:
                    parents[target] = origin
                    queue.append((target, origin))
        return parents

    @cached_property
    def placements(self) -> dict[str, Placed]:
        placed = {const: Placed(WORLD, x * BLOCK_PX, y * BLOCK_PX) for const, (x, y) in self.world_blocks.items()}
        placed |= {const: Placed(const, 0, 0) for const in self.indoor_parents}
        return placed

    @property
    def display_maps(self) -> list[str]:
        indoor = sorted(self.indoor_parents, key=lambda c: self.maps[c].number)
        return [WORLD, *indoor]

    def point(self, const: str, x: int, y: int) -> tuple[int, int]:
        """Centre de la case (x, y) de la carte `const`, en pixels de la carte affichée qui la contient."""
        placed = self.placements[const]
        return placed.x + x * STEP_PX + STEP_PX // 2, placed.y + y * STEP_PX + STEP_PX // 2

    # --- Terrain --------------------------------------------------------------

    def cells(self, const: str) -> dict[str, list[tuple[int, int]]]:
        """Cases (pas de 16 px) de chaque terrain où le jeu fait apparaître des Pokémon sauvages : herbes (grass),
        eau (water) et sol praticable (floor).

        Comme le jeu, on regarde la tuile en bas à gauche de chaque case. Le sol ne compte que dans les cartes
        intérieures hors forêt : ailleurs, marcher hors des herbes ne déclenche aucune rencontre."""
        pret_map = self.maps[const]
        tileset = self.repo.tilesets[pret_map.tileset]
        wild_floor = not pret_map.is_outdoor and pret_map.tileset != FOREST_TILESET
        warps = {(warp.x, warp.y) for warp in pret_map.warps}
        result: dict[str, list[tuple[int, int]]] = {"grass": [], "water": [], "floor": []}
        for y in range(pret_map.height * 2):
            for x in range(pret_map.width * 2):
                if (x, y) in warps:
                    continue
                tile = self.repo.tile_at(pret_map, x * 2, y * 2 + 1)
                if tileset.grass_tile is not None and tile == tileset.grass_tile:
                    result["grass"].append((x, y))
                elif tileset.has_water and tile == WATER_TILE:
                    result["water"].append((x, y))
                elif wild_floor and tile in tileset.passable:
                    result["floor"].append((x, y))
        pairs = self.repo.land_pair_collisions.get(pret_map.tileset, set())

        def blocked(a: tuple[int, int], b: tuple[int, int]) -> bool:
            first = self.repo.tile_at(pret_map, a[0] * 2, a[1] * 2 + 1)
            second = self.repo.tile_at(pret_map, b[0] * 2, b[1] * 2 + 1)
            return frozenset((first, second)) in pairs

        result["floor"] = _reachable(result["floor"], warps, blocked)
        return result

    def wild_terrains(self, const: str) -> frozenset[str]:
        """Terrains de la carte où le jeu fait apparaître des Pokémon sauvages."""
        return frozenset(kind for kind, cells in self.cells(const).items() if cells)

    def spots(self, const: str) -> dict[str, list[tuple[int, int]]]:
        """Emplacements bien répartis de chaque terrain, pour dessiner les Pokémon sauvages."""
        return {
            kind: spread(cells, SPOTS_PER_KIND, f"{const}/{kind}") for kind, cells in self.cells(const).items() if cells
        }
