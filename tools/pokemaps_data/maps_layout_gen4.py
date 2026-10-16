"""Assemblages DS déterminés par les matrices, avec sélection éditoriale explicite des en-têtes."""

from __future__ import annotations

import csv
from dataclasses import dataclass

from .maps import read_map_names
from .maps_plans import read_plans
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_map_models import EMPTY_BLOCK, Gen4Header, Gen4Matrix
from .sources import DATA_DIR

BLOCK_PX = 512
# Cotangentes fx32 des angles des deux tables caméra épinglées ; valeurs relues au prototype.
_COTANGENTS = {
    54786: 2456,
    53090: 1624,
    55586: 2905,
    56418: 3426,
    54787: 2457,
    52227: 1244,
    52707: 1453,
    58147: 4781,
    54467: 2289,
    55011: 2578,
    54019: 2063,
    56835: 3715,
    51268: 843,
}


@dataclass(frozen=True)
class MatrixBlock:
    column: int
    row: int
    block: int
    header: int
    altitude: int


@dataclass(frozen=True)
class MatrixDisplay:
    const: str
    matrix: int
    headers: tuple[int, ...]
    blocks: tuple[MatrixBlock, ...]
    # Bornes en pixels du sol dans la matrice, avant le débord oblique calculé par le rendu.
    bounds: tuple[int, int, int, int]


def camera_cotangent(repo: Gen4PretRepo, header: Gen4Header) -> int:
    angle = repo.cameras[header.camera].angle_x
    if angle not in _COTANGENTS:
        raise ValueError(f"{header.constant} : angle de caméra non relu : {angle}")
    return _COTANGENTS[angle]


def selected_headers(repo: Gen4PretRepo) -> dict[int, Gen4Header]:
    excluded: dict[str, str] = {}
    with (DATA_DIR / "map_exclusions_gen4.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["family"] != repo.variant:
                continue
            if row["map"] in excluded or not row["reason"].strip():
                raise ValueError(f"map_exclusions_gen4.csv : exclusion invalide : {row}")
            excluded[row["map"]] = row["reason"]
    known = {header.constant for header in repo.headers.values()}
    if missing := excluded.keys() - known:
        raise ValueError(f"map_exclusions_gen4.csv : en-têtes inconnus : {sorted(missing)}")
    result = {index: header for index, header in repo.headers.items() if header.constant not in excluded}
    names = read_map_names().get(repo.variant, {})
    if missing := {header.constant for header in result.values()} - names.keys():
        raise ValueError(f"maps.csv : noms français DS manquants : {sorted(missing)}")
    if not result or any(index in result for index in (0, 1)):
        raise ValueError(f"{repo.variant} : sélection DS vide ou en-tête de remplissage affiché")
    return result


def displays(repo: Gen4PretRepo, headers: dict[int, Gen4Header]) -> tuple[MatrixDisplay, ...]:
    groups: dict[tuple[int, int, int], list[int]] = {}
    for index, header in headers.items():
        matrix = repo.matrices[header.matrix]
        # Les matrices portant leurs en-têtes (Sinnoh, Grand Marais) forment un seul assemblage.
        key = (header.matrix, -1, -1) if matrix.headers else (header.matrix, index, header.camera)
        groups.setdefault(key, []).append(index)
    plans = {part.map: part.plan for part in read_plans() if part.family == repo.variant}
    result = []
    for (matrix_id, _, _), members in sorted(groups.items()):
        matrix = repo.matrices[matrix_id]
        const = "SINNOH" if matrix_id == 0 else plans.get(headers[members[0]].constant, headers[members[0]].constant)
        blocks = _matrix_blocks(matrix, members, headers)
        left, top = min(block.column for block in blocks), min(block.row for block in blocks)
        right, bottom = max(block.column for block in blocks) + 1, max(block.row for block in blocks) + 1
        bounds = (left * BLOCK_PX, top * BLOCK_PX, right * BLOCK_PX, bottom * BLOCK_PX)
        result.append(MatrixDisplay(const, matrix_id, tuple(members), blocks, bounds))
    return tuple(result)


def _matrix_blocks(matrix: Gen4Matrix, members: list[int], headers: dict[int, Gen4Header]) -> tuple[MatrixBlock, ...]:
    owners = _owners(matrix, members)
    if not owners:
        raise ValueError(f"matrice {matrix.index} : aucun bloc utilisé")
    left, right = min(x for x, _ in owners), max(x for x, _ in owners)
    top, bottom = min(y for _, y in owners), max(y for _, y in owners)
    result = []
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            block = matrix.blocks[y][x]
            if block == EMPTY_BLOCK:
                continue
            if matrix.headers is not None and matrix.headers[y][x] not in (0, 1, *members):
                continue
            owner = owners.get((x, y))
            if owner is None:
                # Un remplissage est vu avec la zone voisine ; choix stable, sans dépendre du parcours du joueur.
                nearest = min(owners, key=lambda p: (abs(p[0] - x) + abs(p[1] - y), p[1], p[0]))
                owner = owners[nearest]
            if owner not in headers:
                raise ValueError(f"matrice {matrix.index} : propriétaire écarté : {owner}")
            altitude = matrix.altitudes[y][x] if matrix.altitudes else 0
            result.append(MatrixBlock(x, y, block, owner, altitude))
    return tuple(result)


def _owners(matrix: Gen4Matrix, members: list[int]) -> dict[tuple[int, int], int]:
    if matrix.headers is not None:
        return {
            (x, y): value for y, row in enumerate(matrix.headers) for x, value in enumerate(row) if value in members
        }
    return {
        (x, y): members[0] for y, row in enumerate(matrix.blocks) for x, block in enumerate(row) if block != EMPTY_BLOCK
    }
