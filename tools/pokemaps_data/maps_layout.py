"""Sélection et placement des cartes d'un jeu pret, et emplacements où dessiner les Pokémon sauvages.

Chaque région du jeu (games.Region) a sa carte du monde : ses villes et routes y sont placées grâce aux connexions
entre cartes, depuis la ville de départ de la région. Une carte extérieure qu'aucune connexion ne relie à la ville
de départ peut y être ancrée à la main (tools/data/map_anchors.csv) ; sinon, comme une carte intérieure, c'est une
carte à part, rattachée à la ville ou route d'où l'on y entre par un warp.

Les connexions d'un jeu ne forment pas toujours un plan cohérent (Or et Argent décalent Céladopole d'une métatuile
par rapport à la Route 7) : une connexion incohérente arrête la génération, sauf si elle est écartée à la main dans
tools/data/map_connection_skips.csv ; les cartes qu'elle relie sont alors placées par leurs autres connexions.
"""

from __future__ import annotations

import csv
import random
from collections import deque
from dataclasses import dataclass
from functools import cached_property

from .games import Game, Region
from .maps_terrain import ROCK, Cell, wild_cells
from .pret import BLOCK_PX, LAST_MAP, STEP_PX
from .pret_models import HIDDEN_ITEM
from .pret_reader import PretReader
from .sources import DATA_DIR

# Emplacements où dessiner les Pokémon sauvages, par carte et par type de terrain (au plus SPOTS_PER_KIND),
# espacés d'au moins SPOT_SPACING cases pour que les sprites ne se chevauchent pas.
SPOTS_PER_KIND = 40
SPOT_SPACING = 3
# Case « intérieure » : au moins autant de voisines (sur 8) du même terrain.
INTERIOR_NEIGHBORS = 7


def identifier(const: str) -> str:
    return const.lower().replace("_", "-")


@dataclass
class Placed:
    """Position d'une carte pret dans la carte affichée qui la contient."""

    display: str  # constante de la carte affichée (celle de la région pour les villes et routes)
    x: int  # en pixels
    y: int


@dataclass(frozen=True)
class MapAnchor:
    """Carte extérieure placée dans la carte du monde par rapport à une autre, faute de connexion entre elles."""

    family: str  # famille de cartes (games.Game.map_family)
    map: str  # constante de la carte placée
    anchor: str  # constante de la carte de référence, déjà placée
    x: int  # position du coin haut gauche de `map` par rapport à celui de `anchor`, en métatuiles
    y: int


@dataclass(frozen=True)
class ConnectionSkip:
    """Connexion entre deux cartes, dans les deux sens, que le placement ignore (connexion incohérente)."""

    family: str
    map: str
    target: str


@dataclass(frozen=True)
class MapParent:
    """Carte à part atteinte depuis plusieurs villes ou routes : celle d'où l'on y entre normalement."""

    family: str
    map: str
    parent: str  # ville ou route d'une carte du monde, d'où un warp mène directement à `map`


@dataclass(frozen=True)
class LayoutCuration:
    """Ancrages (map_anchors.csv), connexions écartées (map_connection_skips.csv) et origines choisies des cartes à
    part (map_parents.csv), toutes familles confondues."""

    anchors: tuple[MapAnchor, ...]
    skips: tuple[ConnectionSkip, ...]
    parents: tuple[MapParent, ...]


def read_layout_curation() -> LayoutCuration:
    with (DATA_DIR / "map_anchors.csv").open(encoding="utf-8", newline="") as handle:
        anchors = tuple(
            MapAnchor(row["family"], row["map"], row["anchor"], int(row["x"]), int(row["y"]))
            for row in csv.DictReader(handle)
        )
    with (DATA_DIR / "map_connection_skips.csv").open(encoding="utf-8", newline="") as handle:
        skips = tuple(ConnectionSkip(row["family"], row["map"], row["target"]) for row in csv.DictReader(handle))
    with (DATA_DIR / "map_parents.csv").open(encoding="utf-8", newline="") as handle:
        parents = tuple(MapParent(row["family"], row["map"], row["parent"]) for row in csv.DictReader(handle))
    return LayoutCuration(anchors, skips, parents)


def spread(cells: list[Cell], count: int, seed: str, occupied: frozenset[Cell] = frozenset()) -> list[Cell]:
    """Jusqu'à `count` cases réparties au hasard sur tout le terrain, à `SPOT_SPACING` cases au moins les unes
    des autres, hors des cases `occupied` (personnage, objet ou entrée qu'un Pokémon dessiné là masquerait).

    Les cases à l'intérieur du terrain (entourées d'herbes, d'eau ou de sol) passent en premier : les Pokémon
    ne sont pas collés aux bords des zones ni de la carte. Le tirage est déterministe (graine = nom de la carte) et
    ne dépend pas des cases occupées : écarter une case ne déplace pas les autres emplacements."""
    free = set(cells)
    rng = random.Random(seed)
    order = sorted(cells)
    rng.shuffle(order)

    def neighbors(cell: Cell) -> int:
        x, y = cell
        return sum((x + dx, y + dy) in free for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)

    order.sort(key=lambda c: -min(neighbors(c), INTERIOR_NEIGHBORS))
    chosen: list[Cell] = []
    for cell in order:
        if len(chosen) >= count:
            break
        if cell in occupied:
            continue
        if all((cell[0] - x) ** 2 + (cell[1] - y) ** 2 >= SPOT_SPACING**2 for x, y in chosen):
            chosen.append(cell)
    return chosen


class GameMaps:
    """Cartes d'un jeu : sélection, placement et terrain."""

    def __init__(self, repo: PretReader, game: Game, curation: LayoutCuration) -> None:
        self.repo = repo
        self.game = game
        self.maps = repo.maps
        self.anchors = [anchor for anchor in curation.anchors if anchor.family == game.map_family]
        skips = [skip for skip in curation.skips if skip.family == game.map_family]
        for skip in skips:
            if skip.map not in self.maps or skip.target not in {c.target for c in self.maps[skip.map].connections}:
                raise ValueError(f"map_connection_skips.csv : connexion inconnue dans {game.version_group} : {skip}")
        self.skipped = {pair for skip in skips for pair in ((skip.map, skip.target), (skip.target, skip.map))}
        self.chosen_parents = [parent for parent in curation.parents if parent.family == game.map_family]

    # --- Cartes du monde ----------------------------------------------------

    @cached_property
    def world_blocks(self) -> dict[str, dict[str, tuple[int, int]]]:
        """Région -> position (en métatuiles) de chaque ville et route dans sa carte du monde."""
        result = {region.const: self._place_region(region) for region in self.game.regions}
        placed = [const for blocks in result.values() for const in blocks]
        if duplicates := sorted({const for const in placed if placed.count(const) > 1}):
            raise ValueError(f"Cartes dans plusieurs régions : {duplicates}")
        if unused := [anchor for anchor in self.anchors if anchor.map not in placed]:
            raise ValueError(f"map_anchors.csv : ancrages sans carte placée dans {self.game.version_group} : {unused}")
        return result

    def _place_region(self, region: Region) -> dict[str, tuple[int, int]]:
        if region.start_map not in self.maps:
            raise ValueError(f"Ville de départ inconnue pour {region.const} : {region.start_map}")
        positions = {region.start_map: (0, 0)}
        self._follow_connections(positions, region.start_map)
        pending = list(self.anchors)
        while placeable := [anchor for anchor in pending if anchor.anchor in positions]:
            for anchor in placeable:
                pending.remove(anchor)
                if anchor.map in positions:
                    raise ValueError(f"map_anchors.csv : {anchor.map} est déjà relié par une connexion")
                x, y = positions[anchor.anchor]
                positions[anchor.map] = (x + anchor.x, y + anchor.y)
                self._follow_connections(positions, anchor.map)
        self._check_region(region, positions)
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        return {const: (x - min_x, y - min_y) for const, (x, y) in positions.items()}

    def _follow_connections(self, positions: dict[str, tuple[int, int]], start: str) -> None:
        """Place les cartes reliées à `start` par des connexions (parcours borné par le nombre de cartes)."""
        queue = deque([start])
        while queue:
            current = self.maps[queue.popleft()]
            x, y = positions[current.const]
            for connection in current.connections:
                if (current.const, connection.target) in self.skipped:
                    continue
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

    def _check_region(self, region: Region, positions: dict[str, tuple[int, int]]) -> None:
        """Chaque carte placée est une carte extérieure de la région, et aucune n'en recouvre une autre."""
        foreign = sorted(
            const
            for const in positions
            if not self.maps[const].is_outdoor or self.repo.map_region(const) != region.const
        )
        if foreign:
            raise ValueError(f"Cartes placées dans {region.const} sans en être des villes ou routes : {foreign}")
        occupied: dict[tuple[int, int], str] = {}
        for const, (x, y) in sorted(positions.items()):
            pret_map = self.maps[const]
            for cell in ((x + dx, y + dy) for dy in range(pret_map.height) for dx in range(pret_map.width)):
                if cell in occupied:
                    raise ValueError(f"{const} recouvre {occupied[cell]} dans la carte de {region.const}")
                occupied[cell] = const

    def world_size(self, region: str) -> tuple[int, int]:
        """Taille de la carte du monde de la région, en métatuiles."""
        blocks = self.world_blocks[region]
        width = max(x + self.maps[const].width for const, (x, _) in blocks.items())
        height = max(y + self.maps[const].height for const, (_, y) in blocks.items())
        return width, height

    @cached_property
    def world_region(self) -> dict[str, str]:
        """Ville ou route placée dans une carte du monde -> région de cette carte."""
        return {const: region for region, blocks in self.world_blocks.items() for const in blocks}

    # --- Cartes à part --------------------------------------------------------

    @cached_property
    def parents(self) -> dict[str, str]:
        """Cartes à part accessibles par les warps, ou par les scripts qui envoient le joueur ailleurs (intérieurs,
        et villes ou routes hors des cartes du monde) -> ville ou route d'origine, dans une carte du monde.

        Une carte atteinte depuis plusieurs villes ou routes prend la première dans l'ordre des cartes pret, sauf si
        tools/data/map_parents.csv en choisit une ; les cartes qu'on atteint par elle suivent ce choix."""
        chosen = self._chosen_parents()
        parents: dict[str, str] = {}
        queue: deque[tuple[str, str]] = deque()
        for const in sorted(self.world_region, key=lambda c: self.maps[c].number):
            queue.append((const, const))
        while queue:
            const, origin = queue.popleft()
            for target in self._exits(const):
                if target not in self.world_region and target not in parents:
                    parents[target] = chosen.get(target, origin)
                    queue.append((target, parents[target]))
        outdoor = {const for const, pret_map in self.maps.items() if pret_map.is_outdoor}
        if orphans := sorted(outdoor - self.world_region.keys() - parents.keys()):
            raise ValueError(f"Cartes extérieures reliées à aucune carte du monde : {orphans}")
        return parents

    def _exits(self, const: str) -> list[str]:
        """Cartes où le joueur peut aller depuis `const` : warps accessibles et warps de script."""
        pret_map = self.maps[const]
        targets = [*(warp.target for warp in pret_map.warps if warp.accessible), *pret_map.script_warps]
        return [target for target in targets if target != LAST_MAP and target in self.maps]

    def _chosen_parents(self) -> dict[str, str]:
        """Origines imposées par map_parents.csv : chacune est une ville ou route d'où un warp mène à la carte."""
        result = {}
        for chosen in self.chosen_parents:
            if chosen.map in self.world_region or chosen.parent not in self.world_region:
                raise ValueError(f"map_parents.csv : {chosen.parent} -> {chosen.map} ne mène pas d'une carte du monde")
            if chosen.map not in self._exits(chosen.parent):
                raise ValueError(f"map_parents.csv : aucun warp de {chosen.parent} vers {chosen.map}")
            result[chosen.map] = chosen.parent
        return result

    @cached_property
    def placements(self) -> dict[str, Placed]:
        placed = {
            const: Placed(region, x * BLOCK_PX, y * BLOCK_PX)
            for region, blocks in self.world_blocks.items()
            for const, (x, y) in blocks.items()
        }
        placed |= {const: Placed(const, 0, 0) for const in self.parents}
        return placed

    @property
    def display_maps(self) -> list[str]:
        """Cartes affichées : les cartes du monde, puis les cartes à part."""
        detached = sorted(self.parents, key=lambda c: self.maps[c].number)
        return [*(region.const for region in self.game.regions), *detached]

    def point(self, const: str, x: int, y: int) -> tuple[int, int]:
        """Centre de la case (x, y) de la carte `const`, en pixels de la carte affichée qui la contient."""
        placed = self.placements[const]
        return placed.x + x * STEP_PX + STEP_PX // 2, placed.y + y * STEP_PX + STEP_PX // 2

    # --- Terrain --------------------------------------------------------------

    def cells(self, const: str) -> dict[str, list[Cell]]:
        """Cases (pas de 16 px) de chaque terrain où le jeu fait apparaître des Pokémon sauvages (maps_terrain)."""
        return wild_cells(self.repo, self.maps[const])

    def wild_terrains(self, const: str) -> frozenset[str]:
        """Terrains de la carte où le jeu fait apparaître des Pokémon sauvages."""
        return frozenset(kind for kind, cells in self.cells(const).items() if cells)

    def spots(self, const: str) -> dict[str, list[Cell]]:
        """Emplacements bien répartis de chaque terrain, pour dessiner les Pokémon sauvages."""
        return {
            kind: spread(cells, SPOTS_PER_KIND, f"{const}/{kind}", self.occupied(const, kind))
            for kind, cells in self.cells(const).items()
            if cells
        }

    def free_cells(self, const: str) -> dict[str, list[Cell]]:
        """Cases de chaque terrain où un Pokémon sauvage peut être dessiné sans rien masquer (`occupied`)."""
        return {
            kind: [cell for cell in cells if cell not in self.occupied(const, kind)]
            for kind, cells in self.cells(const).items()
        }

    def occupied(self, const: str, kind: str) -> frozenset[Cell]:
        """Cases où un Pokémon dessiné masquerait un personnage, un objet visible ou une entrée. Le terrain des
        rochers d'Éclate-Roc est fait des rochers eux-mêmes : rien n'y est écarté."""
        if kind == ROCK:
            return frozenset()
        pret_map = self.maps[const]
        objects = {(obj.x, obj.y) for obj in pret_map.objects if obj.kind != HIDDEN_ITEM}
        return frozenset(objects | {(warp.x, warp.y) for warp in pret_map.warps})
