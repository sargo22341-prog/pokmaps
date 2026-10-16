"""Blocs de terrain DS (land_data) : attributs des cases, objets posés, modèle 3D et hauteurs du sol (BDHC).

Un bloc mesure 32 × 32 cases de 16 unités ; son en-tête donne la taille de ses quatre parties
(src/overlay005/land_data.c de Platine, même conteneur en Diamant/Perle). Le BDHC de Platine est décompilé
(src/overlay005/bdhc.c) : plaques rectangulaires et plans. Celui de Diamant/Perle, chargé en assembleur, a une
autre forme, relevée sur les 578 blocs : triangles 3D avec leur plan, grille de bandes et listes d'accès ; sa
cohérence (indices, bandes triées, sommets sur leur plan) est vérifiée à la lecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_source import ByteReader, read_binary

BLOCK_TILES = 32
TILE_UNITS = 16
FX_ONE = 4096
_ATTRIBUTES_SIZE = BLOCK_TILES * BLOCK_TILES * 2
_PROP_SIZE = 48
COLLISION_BIT = 0x8000
BEHAVIOR_MASK = 0xFF
# Le moteur de Platine garde au plus dix hauteurs candidates par position (BDHC_NEW_OBJECT_HEIGHT_CANDIDATES…).
MAX_HEIGHT_CANDIDATES = 10
# En-tête BDHC de Diamant/Perle : taille de l'en-tête, puis (taille d'élément, nombre) pour sommets, normales,
# triangles ; deux constantes relevées ; nombre de cellules de la grille et taille d'une bande ; maximums ; tailles
# des bandes et des listes d'accès ; largeur et hauteur de la grille.
_DP_HEADER = "I18H"
_DP_PRELUDE = 68
_DP_CONSTANTS = {"header": 32, "vertex": 12, "normal": 12, "triangle": 12, "unknown": (28, 2), "strip": 10}


@dataclass(frozen=True)
class MapProp:
    """Objet posé : indice dans le jeu d'objets de la zone, position, rotation (ignorée au rendu par le moteur),
    échelle, en fx32."""

    model: int
    position: tuple[int, int, int]
    rotation: tuple[int, int, int]
    scale: tuple[int, int, int]


@dataclass(frozen=True)
class PlatinumBdhc:
    points: tuple[tuple[int, int], ...]  # (x, z)
    normals: tuple[tuple[int, int, int], ...]
    constants: tuple[int, ...]
    plates: tuple[tuple[int, int, int, int], ...]  # (point 1, point 2, normale, constante)
    strips: tuple[tuple[int, int, int], ...]  # (ligne de balayage z, nombre, début dans la liste)
    access: tuple[int, ...]


@dataclass(frozen=True)
class DiamondBdhc:
    bounds: tuple[int, int, int, int]  # x min, z min, x max, z max
    vertices: tuple[tuple[int, int, int], ...]
    normals: tuple[tuple[int, int, int], ...]
    triangles: tuple[tuple[int, int, int, int, int], ...]  # (sommets ×3, normale, constante du plan)
    grid: tuple[int, int]  # colonnes, lignes
    cells: tuple[tuple[int, int], ...]  # (nombre de bandes, première bande)
    strips: tuple[tuple[int, int, int], ...]  # (nombre, ligne de balayage z, début dans la liste)
    access: tuple[int, ...]


@dataclass(frozen=True)
class LandBlock:
    attributes: tuple[int, ...]  # 32 × 32 cases, ligne par ligne : bit 15 = collision, octet bas = comportement
    props: tuple[MapProp, ...]
    model: bytes  # fichier NSBMD du bloc
    bdhc: PlatinumBdhc | DiamondBdhc | None

    def collision(self, x: int, z: int) -> bool:
        return bool(self.attributes[z * BLOCK_TILES + x] & COLLISION_BIT)

    def behavior(self, x: int, z: int) -> int:
        return self.attributes[z * BLOCK_TILES + x] & BEHAVIOR_MASK


def read_land_block(path: Path, *, diamond_pearl: bool) -> LandBlock:
    reader = ByteReader(read_binary(path), str(path))
    sizes = reader.unpack("4I", 0)
    if 16 + sum(sizes) != len(reader.data) or sizes[0] != _ATTRIBUTES_SIZE:
        raise ValueError(f"{path} : tailles de bloc incohérentes : {sizes} pour {len(reader.data)} octets")
    # Le moteur compte les objets par division entière (MapPropManager_Load) : deux blocs portent deux octets
    # de fin de ligne après leurs objets, ignorés de même.
    props = tuple(_prop(reader, 16 + sizes[0] + i * _PROP_SIZE) for i in range(sizes[1] // _PROP_SIZE))
    model_start = 16 + sizes[0] + sizes[1]
    model = reader.slice(model_start, sizes[2])
    if model[:4] != b"BMD0":
        raise ValueError(f"{path} : modèle NSBMD attendu")
    bdhc = None
    if sizes[3]:
        bdhc = read_bdhc(ByteReader(reader.slice(model_start + sizes[2], sizes[3]), f"{path} (BDHC)"), diamond_pearl)
    return LandBlock(reader.unpack(f"{BLOCK_TILES * BLOCK_TILES}H", 16), props, model, bdhc)


def _prop(reader: ByteReader, offset: int) -> MapProp:
    values = reader.unpack("12i", offset)
    return MapProp(values[0], values[1:4], values[4:7], values[7:10])


def read_bdhc(reader: ByteReader, diamond_pearl: bool) -> PlatinumBdhc | DiamondBdhc:
    if reader.slice(0, 4) != b"BDHC":
        raise ValueError(f"{reader.where} : signature BDHC absente")
    return _diamond_bdhc(reader) if diamond_pearl else _platinum_bdhc(reader)


def _platinum_bdhc(reader: ByteReader) -> PlatinumBdhc:
    points, normals, constants, plates, strips, access = reader.unpack("6H", 4)
    offset = 16
    point_values = reader.unpack(f"{2 * points}i", offset)
    offset += 8 * points
    normal_values = reader.unpack(f"{3 * normals}i", offset)
    offset += 12 * normals
    constant_values = reader.unpack(f"{constants}i", offset)
    offset += 4 * constants
    plate_values = reader.unpack(f"{4 * plates}H", offset)
    offset += 8 * plates
    strip_values = [reader.unpack("iHH", offset + 8 * i) for i in range(strips)]
    offset += 8 * strips
    access_values = reader.unpack(f"{access}H", offset)
    if offset + 2 * access != len(reader.data):
        raise ValueError(f"{reader.where} : {len(reader.data) - offset - 2 * access} octets en trop")
    bdhc = PlatinumBdhc(
        tuple(_chunks(point_values, 2)),
        tuple(_chunks(normal_values, 3)),
        constant_values,
        tuple(_chunks(plate_values, 4)),
        tuple(strip_values),
        access_values,
    )
    _check_platinum(bdhc, reader.where)
    return bdhc


def _check_platinum(bdhc: PlatinumBdhc, where: str) -> None:
    for first, second, normal, constant in bdhc.plates:
        if max(first, second) >= len(bdhc.points) or normal >= len(bdhc.normals) or constant >= len(bdhc.constants):
            raise ValueError(f"{where} : plaque hors des tables")
    if any(start + count > len(bdhc.access) for _, count, start in bdhc.strips):
        raise ValueError(f"{where} : bande hors de la liste d'accès")
    if [s[0] for s in bdhc.strips] != sorted(s[0] for s in bdhc.strips):
        raise ValueError(f"{where} : bandes non triées")
    if any(index >= len(bdhc.plates) for index in bdhc.access):
        raise ValueError(f"{where} : liste d'accès hors des plaques")


def _diamond_bdhc(reader: ByteReader) -> DiamondBdhc:
    values = reader.unpack(_DP_HEADER, 4)
    header, vertex, vertices, normal, normals, triangle, triangles, *unknown = values[:9]
    cells, strip_size, max_strips, max_triangles, strips_size, zero_1, access_size, zero_2, width, height = values[9:]
    expected = (header, vertex, normal, triangle, tuple(unknown), strip_size, zero_1, zero_2)
    constants = _DP_CONSTANTS
    if expected != (*(constants[k] for k in ("header", "vertex", "normal", "triangle", "unknown", "strip")), 0, 0):
        raise ValueError(f"{reader.where} : en-tête BDHC de Diamant/Perle inattendu : {values}")
    if width * height != cells or strips_size % strip_size or access_size % 2:
        raise ValueError(f"{reader.where} : grille BDHC incohérente : {values}")
    announced = _DP_PRELUDE + 12 * (vertices + normals + triangles) + 4 * cells + strips_size + access_size
    if announced != len(reader.data):
        raise ValueError(
            f"{reader.where} : BDHC tronqué ou trop long : {announced} octets annoncés, {len(reader.data)}"
        )
    min_x, min_z, max_x, max_z, cell_x, cell_z = reader.unpack("6i", 44)
    # La taille d'une cellule de la grille est l'étendue divisée par le nombre de cellules, arrondie.
    if abs(cell_x * width - (max_x - min_x)) > width or abs(cell_z * height - (max_z - min_z)) > height:
        raise ValueError(f"{reader.where} : grille BDHC incohérente avec son étendue")
    offset = _DP_PRELUDE
    vertex_values = reader.unpack(f"{3 * vertices}i", offset)
    offset += 12 * vertices
    normal_values = reader.unpack(f"{3 * normals}i", offset)
    offset += 12 * normals
    triangle_values = [reader.unpack("4Hi", offset + 12 * i) for i in range(triangles)]
    offset += 12 * triangles
    cell_values = [reader.unpack("HH", offset + 4 * i) for i in range(cells)]
    offset += 4 * cells
    strip_values = [reader.unpack("HiI", offset + strip_size * i) for i in range(strips_size // strip_size)]
    offset += strips_size
    access_values = reader.unpack(f"{access_size // 2}H", offset)
    if offset + access_size != len(reader.data):
        raise ValueError(f"{reader.where} : {len(reader.data) - offset - access_size} octets de BDHC attendus en plus")
    bdhc = DiamondBdhc(
        (min_x, min_z, max_x, max_z),
        tuple(_chunks(vertex_values, 3)),
        tuple(_chunks(normal_values, 3)),
        tuple(triangle_values),
        (width, height),
        tuple(cell_values),
        tuple(strip_values),
        access_values,
    )
    _check_diamond(bdhc, (max_strips, max_triangles), reader.where)
    return bdhc


def _check_diamond(bdhc: DiamondBdhc, maximums: tuple[int, int], where: str) -> None:
    if any(start + count > len(bdhc.strips) or count > maximums[0] for count, start in bdhc.cells):
        raise ValueError(f"{where} : cellule hors des bandes")
    if any(start + count > len(bdhc.access) or count > maximums[1] for count, _, start in bdhc.strips):
        raise ValueError(f"{where} : bande hors de la liste d'accès")
    for count, start in bdhc.cells:
        lines = [bdhc.strips[start + i][1] for i in range(count)]
        if lines != sorted(lines):
            raise ValueError(f"{where} : bandes d'une cellule non triées")
    if any(index >= len(bdhc.triangles) for index in bdhc.access):
        raise ValueError(f"{where} : liste d'accès hors des triangles")
    for *corners, normal, constant in bdhc.triangles:
        if max(corners) >= len(bdhc.vertices) or normal >= len(bdhc.normals):
            raise ValueError(f"{where} : triangle hors des tables")
        n = bdhc.normals[normal]
        for x, y, z in (bdhc.vertices[corner] for corner in corners):
            # Un sommet est sur le plan du triangle, à une unité fx32 près (arrondi des données).
            if abs((n[0] * x + n[1] * y + n[2] * z) // FX_ONE + constant) > FX_ONE:
                raise ValueError(f"{where} : sommet hors du plan de son triangle")


def _chunks(values: tuple[int, ...], size: int) -> list[tuple[int, ...]]:
    return [tuple(values[i : i + size]) for i in range(0, len(values), size)]


def fx_mul(a: int, b: int) -> int:
    """FX_Mul du Nitro SDK : produit 64 bits arrondi, ramené en fx32."""
    return (a * b + 0x800) >> 12


def fx_div(numerator: int, denominator: int) -> int:
    """FX_Div du Nitro SDK : quotient 32.32 du diviseur matériel (tronqué vers zéro), arrondi en fx32."""
    shifted = numerator << 32
    quotient = abs(shifted) // abs(denominator)
    if (shifted < 0) != (denominator < 0):
        quotient = -quotient
    return (quotient + (1 << 19)) >> 20


def heights(bdhc: PlatinumBdhc | DiamondBdhc, x: int, z: int) -> tuple[int, ...]:
    """Hauteurs (fx32) des surfaces sous le point (x, z) relatif au centre du bloc, de la plus basse à la plus
    haute ; plusieurs valeurs signalent des niveaux superposés, entre lesquels le moteur choisit la plus proche
    de la hauteur courante."""
    if isinstance(bdhc, PlatinumBdhc):
        found = {
            _plane_height(bdhc.normals[normal], bdhc.constants[constant], x, z)
            for first, second, normal, constant in bdhc.plates
            if _in_box(bdhc.points[first], bdhc.points[second], x, z) and bdhc.normals[normal][1]
        }
    else:
        found = {
            _plane_height(bdhc.normals[normal], constant, x, z)
            for *corners, normal, constant in bdhc.triangles
            if _in_triangle([bdhc.vertices[c] for c in corners], x, z) and bdhc.normals[normal][1]
        }
    return tuple(sorted(found))


def _plane_height(normal: tuple[int, ...], constant: int, x: int, z: int) -> int:
    # Plan Ax + By + Cz + D = 0 résolu en y, comme CalculateObjectHeight.
    return fx_div(-(fx_mul(normal[0], x) + fx_mul(normal[2], z) + constant), normal[1])


def _in_box(first: tuple[int, ...], second: tuple[int, ...], x: int, z: int) -> bool:
    return min(first[0], second[0]) <= x <= max(first[0], second[0]) and min(first[1], second[1]) <= z <= max(
        first[1], second[1]
    )


def _in_triangle(corners: list[tuple[int, ...]], x: int, z: int) -> bool:
    """Le point (x, z) est dans la projection horizontale du triangle, bords compris."""
    signs = []
    for (ax, _, az), (bx, _, bz) in zip(corners, corners[1:] + corners[:1], strict=True):
        cross = (bx - ax) * (z - az) - (bz - az) * (x - ax)
        if cross:
            signs.append(cross > 0)
    return len(set(signs)) <= 1 and bool(signs)
