"""Surfaces praticables superposées, relevées dans le BDHC plutôt que dans les objets de décor."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from .pret_gen4_land import BLOCK_TILES, FX_ONE, LandBlock, heights


@dataclass(frozen=True)
class LowerSurface:
    ceiling: int
    cells: tuple[tuple[int, int], ...]


def lower_surfaces(block: LandBlock, altitude: int) -> tuple[LowerSurface, ...]:
    if block.bdhc is None:
        return ()
    layers: dict[int, dict[tuple[int, int], int]] = {}
    for z in range(BLOCK_TILES):
        for x in range(BLOCK_TILES):
            if block.collision(x, z):
                continue
            values = heights(block.bdhc, (x * 16 - 248) * FX_ONE, (z * 16 - 248) * FX_ONE)
            if len(values) < 2:
                continue
            # Une différence d'au moins une case écarte les petites marches et les surfaces de mobilier.
            for level, (lower, upper) in enumerate(pairwise(values)):
                if upper - lower >= 16 * FX_ONE:
                    layers.setdefault(level, {})[x, z] = upper
    result = []
    for cells in layers.values():
        connected = _connected_cells(set(cells))
        if connected:
            ceiling = min(cells[cell] for cell in connected) - 1 + altitude * 8 * FX_ONE
            result.append(LowerSurface(ceiling, tuple(sorted(connected))))
    return tuple(result)


def _connected_cells(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    remaining = set(cells)
    while remaining:
        start = min(remaining)
        pending, component = [start], set()
        while pending:
            cell = pending.pop()
            if cell not in remaining:
                continue
            remaining.remove(cell)
            component.add(cell)
            x, y = cell
            pending.extend(p for p in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if p in remaining)
        if len(component) >= 4:
            result.update(component)
    return result
