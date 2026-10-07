"""Terrain où le jeu fait apparaître des Pokémon sauvages : herbes (grass), eau (water) et sol (floor).

Les cases sont en pas de 16 px. Chaque format pret a sa règle, celle de son moteur :
- 1re génération : la tuile en bas à gauche de la case (tuile d'herbe du tileset, tuile d'eau) ; le sol ne compte
  que dans les cartes intérieures hors forêt (TryDoWildEncounter) ;
- 2e génération : la collision de la case (CanEncounterWildMon) ; en grotte ou en donjon, chaque pas hors de la
  glace, ailleurs seulement les collisions d'herbe et d'eau de CheckGrassCollision.

Le sol est restreint aux cases accessibles à pied depuis les warps : le bord des grottes est souvent praticable
mais isolé.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from .pret import WATER_TILE, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_models import PretMap
from .pret_reader import PretReader

Cell = tuple[int, int]
TERRAINS = ("grass", "water", "floor")

# 1re génération : tileset de la forêt de Jade et du Parc Safari, où l'on ne rencontre des Pokémon qu'en marchant
# dans les herbes, comme dehors (engine/battle/wild_encounters.asm, TryDoWildEncounter).
FOREST_TILESET = "FOREST"
# 2e génération : environnements où chaque pas peut déclencher une rencontre (CanEncounterWildMon).
WILD_FLOOR_ENVIRONMENTS = frozenset({"CAVE", "DUNGEON"})
_LAND, _WATER, _TALK = "LAND_TILE", "WATER_TILE", "|TALK"


def wild_cells(repo: PretReader, pret_map: PretMap) -> dict[str, list[Cell]]:
    """Cases de chaque terrain de la carte où le jeu fait apparaître des Pokémon sauvages."""
    warps = {(warp.x, warp.y) for warp in pret_map.warps}
    match repo:
        case PretRepo():
            cells, blocked = _gen1_cells(repo, pret_map, warps)
        case Gen2PretRepo():
            cells, blocked = _gen2_cells(repo, pret_map, warps)
    cells["floor"] = reachable(cells["floor"], warps, blocked)
    return cells


def reachable(cells: list[Cell], starts: set[Cell], blocked: Callable[[Cell, Cell], bool]) -> list[Cell]:
    """Cases de `cells` accessibles à pied depuis les cases `starts` (toutes si `starts` est vide)."""
    free = set(cells)
    if not starts:
        return cells
    seen: set[Cell] = set()
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


def _gen1_cells(
    repo: PretRepo, pret_map: PretMap, warps: set[Cell]
) -> tuple[dict[str, list[Cell]], Callable[[Cell, Cell], bool]]:
    """Comme le jeu, on regarde la tuile en bas à gauche de chaque case."""
    tileset = repo.tilesets[pret_map.tileset]
    wild_floor = not pret_map.is_outdoor and pret_map.tileset != FOREST_TILESET
    result: dict[str, list[Cell]] = {kind: [] for kind in TERRAINS}
    for y in range(pret_map.height * 2):
        for x in range(pret_map.width * 2):
            if (x, y) in warps:
                continue
            tile = repo.tile_at(pret_map, x * 2, y * 2 + 1)
            if tileset.grass_tile is not None and tile == tileset.grass_tile:
                result["grass"].append((x, y))
            elif tileset.has_water and tile == WATER_TILE:
                result["water"].append((x, y))
            elif wild_floor and tile in tileset.passable:
                result["floor"].append((x, y))
    pairs = repo.land_pair_collisions.get(pret_map.tileset, set())

    def blocked(a: Cell, b: Cell) -> bool:
        first = repo.tile_at(pret_map, a[0] * 2, a[1] * 2 + 1)
        second = repo.tile_at(pret_map, b[0] * 2, b[1] * 2 + 1)
        return frozenset((first, second)) in pairs

    return result, blocked


def _gen2_cells(
    repo: Gen2PretRepo, pret_map: PretMap, warps: set[Cell]
) -> tuple[dict[str, list[Cell]], Callable[[Cell, Cell], bool]]:
    """Collision de chaque case : herbes et eau partout, sol seulement en grotte ou en donjon."""
    tileset = repo.tilesets[pret_map.tileset]
    rules = repo.collisions
    everywhere = repo.headers[pret_map.const].environment in WILD_FLOOR_ENVIRONMENTS
    result: dict[str, list[Cell]] = {kind: [] for kind in TERRAINS}
    for y in range(pret_map.height * 2):
        for x in range(pret_map.width * 2):
            collision = tileset.collisions[pret_map.block(x // 2, y // 2)][(y % 2) * 2 + x % 2]
            permission = rules.permissions[collision]
            if (x, y) in warps or permission.endswith(_TALK) or collision in rules.ice:
                continue
            grass = collision in rules.grass
            if permission == _WATER and (grass or everywhere):
                result["water"].append((x, y))
            elif permission == _LAND and grass:
                result["grass"].append((x, y))
            elif permission == _LAND and everywhere:
                result["floor"].append((x, y))
    return result, _never_blocked


def _never_blocked(_a: Cell, _b: Cell) -> bool:
    """2e génération : deux cases de sol voisines sont toujours reliées (les murs n'ont pas la permission LAND_TILE)."""
    return False
