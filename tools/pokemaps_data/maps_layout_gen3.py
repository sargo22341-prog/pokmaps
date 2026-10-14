"""Assemblage GBA, avec les variantes propres à Hoenn et aux remakes de Kanto."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import replace
from functools import cached_property

from .games import Game, Region
from .maps_curation_gen3 import choose_layouts, read_layout_choices, read_trims, trim_maps
from .maps_layout import GameMaps, LayoutCuration
from .maps_terrain_gen3 import wild_cells
from .maps_versions_gen3 import version_maps
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Map
from .pret_gen3_source import read_text

UNDERWATER = "HOENN_UNDERWATER"
# L'Île Mirage est le Chenal 130 avec un autre layout : elle se superpose à la route dans la carte du monde.
MIRAGE_ISLAND = "MAP_ROUTE130_MIRAGE_ISLAND"
MIRAGE_ROUTE = "MAP_ROUTE130"


class Gen3GameMaps(GameMaps):
    block_px = 16

    def cells(self, const: str) -> dict[str, list[tuple[int, int]]]:
        return wild_cells(self.repo, self.maps[const])

    @property
    def world_numbers(self) -> dict[str, int]:
        return super().world_numbers if self.repo.remake else super().world_numbers | {UNDERWATER: 994}

    def __init__(self, repo: Gen3PretRepo, game: Game, curation: LayoutCuration) -> None:
        regions = tuple(replace(region, start_map=f"MAP_{region.start_map}") for region in game.regions)
        curation = (
            curation
            if repo.remake
            else replace(
                curation,
                anchors=tuple(anchor for anchor in curation.anchors if anchor.map in repo.maps),
                skips=tuple(skip for skip in curation.skips if skip.map in repo.maps and skip.target in repo.maps),
                parents=tuple(
                    parent for parent in curation.parents if parent.map in repo.maps or parent.map == MIRAGE_ISLAND
                ),
            )
        )
        super().__init__(repo, replace(game, regions=regions), curation)
        # Ces layouts ne sont jamais utilisés par le moteur commercial ; aucun prototype n'est affiché.
        self.maps = {
            const: current
            for const, current in repo.maps.items()
            if not any(marker in const for marker in ("UNUSED", "PROTOTYPE", "UNKNOWN_MAP"))
        }
        family = game.map_family
        choose_layouts(self.maps, repo, [choice for choice in read_layout_choices() if choice.family == family])
        trim_maps(self.maps, [trim for trim in read_trims() if trim.family == family])
        if repo.remake:
            curated = {entry.map for entry in (*self.anchors, *self.chosen_parents, *self.plan_parts)}
            if missing := sorted(curated - self.maps.keys()):
                raise ValueError(f"Cartes de remake éditoriales absentes ou inutilisées : {missing}")
            return
        self.maps[MIRAGE_ISLAND] = replace(
            self.maps[MIRAGE_ROUTE],
            const=MIRAGE_ISLAND,
            number=800,
            layout=repo.layouts["LAYOUT_UNREFERENCED_MAP" if repo.ruby else "LAYOUT_ROUTE130_MIRAGE_ISLAND"],
            connections=(),
            warps=(),
        )
        self._tide_events()

    def _tide_events(self) -> None:
        for const in ("MAP_SHOAL_CAVE_HIGH_TIDE_ENTRANCE_ROOM", "MAP_SHOAL_CAVE_HIGH_TIDE_INNER_ROOM"):
            high = self.maps[const]
            low = self.maps[const.replace("HIGH_TIDE", "LOW_TIDE")]
            warps = tuple(
                replace(
                    warp,
                    target=warp.target.replace("LOW_TIDE", "HIGH_TIDE")
                    if warp.target.replace("LOW_TIDE", "HIGH_TIDE") in self.maps
                    else warp.target,
                    accessible=self._behavior(high, warp.x, warp.y) == self._behavior(low, warp.x, warp.y),
                )
                for warp in low.warps
            )
            self.maps[const] = replace(high, warps=warps, objects=low.objects, bg_events=low.bg_events)

    def _behavior(self, current: Gen3Map, x: int, y: int) -> int:
        number = current.block(x, y)
        primary = self.repo.tilesets[current.layout.primary_tileset]
        secondary = self.repo.tilesets[current.layout.secondary_tileset]
        source = primary if number < primary.primary_metatile_count else secondary
        index = number if source is primary else number - primary.primary_metatile_count
        return source.metatiles[index].behavior

    def _check_region(self, region: Region, positions: dict[str, tuple[int, int]]) -> None:
        if any(not self.maps[const].is_outdoor for const in positions):
            raise ValueError(f"{region.const} : carte intérieure dans le monde extérieur")
        self._check_overlap(region.const, positions)

    def _check_overlap(self, level: str, positions: dict[str, tuple[int, int]]) -> None:
        occupied: dict[tuple[int, int], str] = {}
        for const, (x, y) in positions.items():
            current = self.maps[const]
            for dy in range(current.height):
                for dx in range(current.width):
                    point = (x + dx, y + dy)
                    if point in occupied:
                        raise ValueError(f"{level} : {const} recouvre {occupied[point]}")
                    occupied[point] = const

    @cached_property
    def world_blocks(self) -> dict[str, dict[str, tuple[int, int]]]:
        surface = super().world_blocks
        if self.repo.remake:
            return surface
        underwater: dict[str, tuple[int, int]] = {}
        for positions in surface.values():
            for const, position in positions.items():
                for connection in self.maps[const].connections:
                    if connection.direction != "dive":
                        continue
                    if connection.offset != 0:
                        raise ValueError(f"{const} : décalage de Plongée inconnu")
                    target = self.maps[connection.target]
                    if target.map_type != "MAP_TYPE_UNDERWATER":
                        raise ValueError(f"{const} : destination de Plongée non sous-marine")
                    if (target.width, target.height) != (self.maps[const].width, self.maps[const].height):
                        raise ValueError(f"{const} : dimensions sous-marines incohérentes")
                    if underwater.get(target.const, position) != position:
                        raise ValueError(f"{target.const} : plusieurs positions de Plongée")
                    underwater[target.const] = position
        self._check_overlap(UNDERWATER, underwater)
        return surface | {UNDERWATER: underwater}

    def _exits(self, const: str) -> list[str]:
        return self.exits(const)

    def exits(self, const: str, closed: frozenset[int] = frozenset()) -> list[str]:
        """Cartes atteintes depuis `const`, sauf par ses warps d'indice `closed` (fermés dans une version)."""
        current = self.maps[const]
        targets = [
            warp.target for index, warp in enumerate(current.warps) if warp.accessible and index not in closed
        ] + [connection.target for connection in current.connections if connection.direction in {"dive", "emerge"}]
        path = self.repo.root / "data/maps" / (current.shared_scripts_map or current.label) / "scripts.inc"
        if path.is_file():
            text = read_text(path)
            targets += re.findall(r"^\s*(?:warp\w*|set\w*warp)\s+(MAP_\w+)", text, re.M)
        return [target for target in targets if target in self.maps]

    def detached_origin(self, const: str) -> tuple[int, int]:
        if const != MIRAGE_ISLAND:
            return 0, 0
        x, y = self.world_blocks[self.world_region[MIRAGE_ROUTE]][MIRAGE_ROUTE]
        return x * self.block_px, y * self.block_px

    @cached_property
    def mirage_cells(self) -> frozenset[tuple[int, int]]:
        """Cases où l'Île Mirage change le Chenal 130 : seules elles sont dessinées par-dessus la route."""
        if MIRAGE_ISLAND not in self.maps:
            return frozenset()
        island, route = self.maps[MIRAGE_ISLAND], self.maps[MIRAGE_ROUTE]
        cells = frozenset(
            (x, y) for y in range(island.height) for x in range(island.width) if island.block(x, y) != route.block(x, y)
        )
        if not cells:
            raise ValueError("Île Mirage : layout identique au Chenal 130")
        return cells

    @cached_property
    def version_maps(self) -> dict[str, str]:
        """Cartes qu'une seule version du groupe permet d'atteindre -> cette version."""
        return version_maps(self)

    @cached_property
    def parents(self) -> dict[str, str]:
        roots = self.world_region
        parents = {entry.map: entry.parent for entry in self.chosen_parents}
        if any(const not in self.maps or parent not in roots or const in roots for const, parent in parents.items()):
            raise ValueError("map_parents.csv : origine GBA absente ou carte déjà dans le monde")
        queue = deque([*((const, const) for const in roots), *parents.items()])
        visited: set[str] = set()
        while queue:
            const, origin = queue.popleft()
            if const in visited:
                continue
            visited.add(const)
            for target in self._exits(const):
                if target not in roots and target not in parents:
                    parents[target] = origin
                    queue.append((target, origin))
        if missing := sorted(self.maps.keys() - roots.keys() - parents.keys()):
            raise ValueError(f"Cartes GBA sans origine (map_parents.csv) : {missing}")
        return parents

    @property
    def display_maps(self) -> list[str]:
        return super().display_maps if self.repo.remake else [*super().display_maps, UNDERWATER]
