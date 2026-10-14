"""Cartes GBA qu'une seule version d'un groupe permet d'atteindre.

Le script de chargement de Nénucrique ouvre l'entrée de la Planque Magma dans Rubis et laisse celle de la
Planque Aqua dans Saphir : les métatuiles posées par `setmetatile` diffèrent entre les deux versions. Un warp
dont la case n'est praticable que dans certaines versions est bloqué dans les autres ; les cartes qu'on ne
peut atteindre qu'à travers lui n'appartiennent alors qu'aux versions où il est ouvert.

Le dessin des cartes est commun au groupe : les cases qu'une version retouche ainsi forment un calque propre à
cette version, dessiné par-dessus la carte du monde.
"""

from __future__ import annotations

import re
from collections import deque
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_gen3_maps import Gen3Map

if TYPE_CHECKING:
    from .maps_layout_gen3 import Gen3GameMaps

_ON_LOAD = re.compile(r"^\s*map_script\s+MAP_SCRIPT_ON_LOAD\s*,\s*(\w+)\s*$", re.M)
_METATILE_LABEL = re.compile(r"^#define\s+(METATILE_\w+)\s+(0x[0-9A-Fa-f]+|\d+)\s*$", re.M)
# Case (x, y) -> (métatuile posée, collision).
_Placed = dict[tuple[int, int], tuple[str, int]]


def version_maps(game_maps: Gen3GameMaps) -> dict[str, str]:
    """Carte -> seule version du groupe où le joueur peut l'atteindre ; les autres cartes sont communes."""
    versions = [version for version, _ in game_maps.repo.versions]
    if len(versions) < 2:
        return {}
    blocked = _blocked_warps(game_maps, versions)
    if not any(blocked.values()):
        return {}
    reached = {version: _reachable(game_maps, blocked[version]) for version in versions}
    result = {}
    for const in game_maps.maps:
        present = [version for version in versions if const in reached[version]]
        if len(present) == 1:
            result[const] = present[0]
    return result


def version_patches(game_maps: Gen3GameMaps) -> dict[str, dict[str, dict[tuple[int, int], int]]]:
    """Version -> carte du monde -> case -> numéro de la métatuile que seule cette version pose au chargement."""
    versions = [version for version, _ in game_maps.repo.versions]
    if len(versions) < 2:
        return {}
    result: dict[str, dict[str, dict[tuple[int, int], int]]] = {}
    for const, current in sorted(game_maps.maps.items()):
        placed = {version: _load_metatiles(game_maps, current, version) for version in versions}
        for version in versions:
            # Une case est propre à la version si une autre version n'y pose pas la même métatuile.
            cells = {
                cell: name
                for cell, (name, collision) in placed[version].items()
                if any(placed[other].get(cell) != (name, collision) for other in versions if other != version)
            }
            if not cells:
                continue
            if const not in game_maps.world_region:
                raise ValueError(f"{const} : métatuiles propres à {version} hors de la carte du monde")
            numbers = _metatile_numbers(game_maps.repo.root)
            if missing := sorted(set(cells.values()) - numbers.keys()):
                raise ValueError(f"{const} : métatuiles inconnues : {missing}")
            result.setdefault(version, {})[const] = {cell: numbers[name] for cell, name in cells.items()}
    return result


@cache
def _metatile_numbers(root: Path) -> dict[str, int]:
    text = (root / "include/constants/metatile_labels.h").read_text("utf-8")
    return {name: int(value, 0) for name, value in _METATILE_LABEL.findall(text)}


def _blocked_warps(game_maps: Gen3GameMaps, versions: list[str]) -> dict[str, set[tuple[str, int]]]:
    """Version -> warps (carte, indice) fermés dans cette version mais ouverts dans une autre."""
    result: dict[str, set[tuple[str, int]]] = {version: set() for version in versions}
    for const, current in sorted(game_maps.maps.items()):
        metatiles = {version: _load_metatiles(game_maps, current, version) for version in versions}
        if all(placed == metatiles[versions[0]] for placed in metatiles.values()):
            continue
        for index, warp in enumerate(current.warps):
            passable = {version: _collision(current, metatiles[version], warp.x, warp.y) == 0 for version in versions}
            if any(passable.values()):
                for version in versions:
                    if not passable[version]:
                        result[version].add((const, index))
    return result


def _load_metatiles(game_maps: Gen3GameMaps, current: Gen3Map, version: str) -> _Placed:
    """Métatuiles et collisions que le script de chargement pose directement, dans la version donnée."""
    relative = f"data/maps/{current.shared_scripts_map or current.label}/scripts.inc"
    if not (game_maps.repo.root / relative).is_file():
        return {}
    match = _ON_LOAD.search(game_maps.repo.source_text(relative, version))
    if match is None:
        return {}
    # Le script peut être commun à plusieurs cartes et défini hors du fichier de la carte.
    block = game_maps.repo.offers[version].scripts.blocks.get(match[1])
    if block is None:
        raise ValueError(f"{relative} : script de chargement absent : {match[1]}")
    placed = {}
    for instruction in block.lines:
        if instruction.command != "setmetatile":
            continue
        if len(instruction.args) != 4 or instruction.args[3] not in {"0", "1", "TRUE", "FALSE"}:
            raise ValueError(f"{instruction.source} : setmetatile inattendu : {instruction.args}")
        collision = 1 if instruction.args[3] in {"1", "TRUE"} else 0
        placed[int(instruction.args[0]), int(instruction.args[1])] = (instruction.args[2], collision)
    return placed


def _collision(current: Gen3Map, placed: _Placed, x: int, y: int) -> int:
    if (x, y) in placed:
        return placed[x, y][1]
    return (current.layout.cells[y * current.width + x] >> 10) & 3


def _reachable(game_maps: Gen3GameMaps, blocked: set[tuple[str, int]]) -> set[str]:
    """Cartes atteintes depuis les cartes du monde sans emprunter les warps bloqués (parcours borné)."""
    reached = set(game_maps.world_region)
    queue = deque(reached)
    while queue:
        const = queue.popleft()
        closed = frozenset(index for source, index in blocked if source == const)
        for target in game_maps.exits(const, closed):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached
