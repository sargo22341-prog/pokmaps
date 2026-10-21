"""Conteneurs natifs HGSS : archives NARC, matrices et blocs avec préambule de vingt octets."""

from pathlib import Path

from .pret_gen4_land import LandBlock, MapProp, read_bdhc
from .pret_gen4_map_models import Gen4Matrix
from .pret_gen4_source import ByteReader, read_binary

_MAX_ARCHIVE_BYTES = 32 * 1024 * 1024


def read_archive(path: Path) -> tuple[bytes, ...]:
    """Lit les trois sections NARC et contrôle chaque intervalle avant de l'exposer."""
    reader = ByteReader(read_binary(path, _MAX_ARCHIVE_BYTES), str(path))
    if reader.unpack("4sHHIHH", 0) != (b"NARC", 0xFFFE, 0x100, len(reader.data), 16, 3):
        raise ValueError(f"{path} : en-tête NARC HGSS invalide")
    sections = {}
    offset = 16
    for expected in (b"BTAF", b"BTNF", b"GMIF"):
        tag, size = reader.unpack("4sI", offset)
        if tag != expected or not 8 <= size <= len(reader.data) - offset:
            raise ValueError(f"{path} : section NARC {expected!r} attendue")
        sections[tag] = reader.slice(offset + 8, size - 8)
        offset += size
    if offset != len(reader.data):
        raise ValueError(f"{path} : octets après les sections NARC")
    table = ByteReader(sections[b"BTAF"], f"{path} BTAF")
    count, reserved = table.unpack("HH", 0)
    if not 0 < count <= 4096 or reserved or len(table.data) != 4 + 8 * count:
        raise ValueError(f"{path} : table des membres NARC invalide")
    payload = ByteReader(sections[b"GMIF"], f"{path} GMIF")
    members = []
    previous = 0
    for index in range(count):
        start, end = table.unpack("II", 4 + 8 * index)
        if start < previous or end < start:
            raise ValueError(f"{path} : intervalle du membre {index} invalide")
        members.append(payload.slice(start, end - start))
        previous = end
    return tuple(members)


def read_matrix(data: bytes, index: int, where: str) -> Gen4Matrix:
    """MapMatrix_MapMatrixData_Load : cases 32 × 32, altitudes par pas de huit unités."""
    reader = ByteReader(data, where)
    width, height, has_headers, has_altitudes, length = reader.unpack("5B", 0)
    if not width or not height or width * height > 799 or length > 16:
        raise ValueError(f"{where} : dimensions ou nom de matrice HGSS invalides")
    if has_headers not in (0, 1) or has_altitudes not in (0, 1):
        raise ValueError(f"{where} : drapeaux de matrice HGSS invalides")
    name = reader.slice(5, length).decode("ascii")
    offset = 5 + length
    grids = []
    for present, fmt, size in ((has_headers, "H", 2), (has_altitudes, "B", 1), (1, "H", 2)):
        grid = None
        if present:
            values = reader.unpack(f"{width * height}{fmt}", offset)
            grid = tuple(values[row : row + width] for row in range(0, len(values), width))
            offset += width * height * size
        grids.append(grid)
    if offset != len(data):
        raise ValueError(f"{where} : taille de matrice HGSS incohérente")
    return Gen4Matrix(index, name, grids[2], grids[0], grids[1])


def read_land(data: bytes, where: str) -> LandBlock:
    """HGSS ajoute magic 0x1234 et une section auxiliaire avant les objets posés."""
    reader = ByteReader(data, where)
    attributes, props, model, bdhc, magic, auxiliary = reader.unpack("4I2H", 0)
    if (
        magic != 0x1234
        or attributes != 2048
        or props % 48
        or 20 + sum((attributes, auxiliary, props, model, bdhc)) != len(data)
    ):
        raise ValueError(f"{where} : tailles ou signature du terrain HGSS invalides")
    prop_start = 20 + attributes + auxiliary
    objects = []
    for offset in range(prop_start, prop_start + props, 48):
        values = reader.unpack("12i", offset)
        objects.append(MapProp(values[0], values[1:4], values[4:7], values[7:10]))
    start = prop_start + props
    model_data = reader.slice(start, model)
    if model_data[:4] != b"BMD0":
        raise ValueError(f"{where} : modèle NSBMD absent")
    surface = read_bdhc(ByteReader(reader.slice(start + model, bdhc), f"{where} BDHC"), False) if bdhc else None
    return LandBlock(reader.unpack("1024H", 20), tuple(objects), model_data, surface)
