"""Fichiers binaires extraits de Diamant/Perle (files/fielddata/**/narc_NNNN.bin) : matrices, événements, zones
et jeux d'objets posés.

Chaque fichier est déjà un membre extrait d'archive NARC : aucun dépaquetage n'est fait ici. Les formats sont
ceux que la construction de Platine produit à partir de ses JSON (tools/jsoncnv/map_matrix.py, event.py,
area_data.py, prop_model_set.py) et que le moteur commun aux deux jeux relit ; chaque taille est vérifiée
exactement, si bien qu'une forme différente arrête la lecture.
"""

from __future__ import annotations

import re
from pathlib import Path

from .pret_gen4_map_models import (
    BgEvent,
    CoordEvent,
    Gen4Area,
    Gen4Events,
    Gen4Matrix,
    ObjectEvent,
    WarpEvent,
)
from .pret_gen4_source import ByteReader, read_binary

FIELD_DATA = "files/fielddata"
# Membres « narc_NNNN.ext » : l'extension varie (bin, NSBMD, NSBTX…) ; .knarcignore règle l'empaquetage.
_MEMBER = re.compile(r"^narc_(\d{4})\.\w+$")
_PACKING_FILES = frozenset({".knarcignore"})
_MAX_MEMBER_BYTES = 64 * 1024
_BG_SIZE, _OBJECT_SIZE, _WARP_SIZE, _COORD_SIZE = 20, 32, 12, 16
_AREA_SIZE = 8


def members(folder: Path) -> dict[int, Path]:
    """Membres numérotés d'une archive extraite, sans trou dans la numérotation."""
    found = {}
    for path in folder.iterdir():
        if path.name in _PACKING_FILES:
            continue
        match = _MEMBER.match(path.name)
        if match is None:
            raise ValueError(f"{folder} : fichier inattendu : {path.name}")
        if int(match.group(1)) in found:
            raise ValueError(f"{folder} : membre répété : {path.name}")
        found[int(match.group(1))] = path
    if sorted(found) != list(range(len(found))) or not found:
        raise ValueError(f"{folder} : numérotation des membres incomplète")
    return found


def read_dp_matrices(root: Path) -> dict[int, Gen4Matrix]:
    return {
        index: _matrix(index, ByteReader(read_binary(path, _MAX_MEMBER_BYTES), str(path)))
        for index, path in members(root / FIELD_DATA / "mapmatrix/map_matrix").items()
    }


def _matrix(index: int, reader: ByteReader) -> Gen4Matrix:
    width, height, has_headers, has_altitudes, name_length = reader.unpack("5B", 0)
    if has_headers not in (0, 1) or has_altitudes not in (0, 1):
        raise ValueError(f"{reader.where} : drapeaux de matrice invalides")
    name = reader.slice(5, name_length).decode("ascii")
    cells = width * height
    offset = 5 + name_length
    headers = None
    if has_headers:
        headers = _grid(reader.unpack(f"{cells}H", offset), width)
        offset += 2 * cells
    altitudes = None
    if has_altitudes:
        altitudes = _grid(reader.unpack(f"{cells}B", offset), width)
        offset += cells
    blocks = _grid(reader.unpack(f"{cells}H", offset), width)
    if offset + 2 * cells != len(reader.data):
        raise ValueError(f"{reader.where} : {len(reader.data) - offset - 2 * cells} octets en trop")
    return Gen4Matrix(index, name, blocks, headers, altitudes)


def _grid(values: tuple[int, ...], width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(values[row : row + width]) for row in range(0, len(values), width))


def read_dp_events(root: Path) -> dict[int, Gen4Events]:
    return {
        index: read_compiled_events(index, ByteReader(read_binary(path, _MAX_MEMBER_BYTES), str(path)))
        for index, path in members(root / FIELD_DATA / "eventdata/zone_event_release").items()
    }


def read_compiled_events(index: int, reader: ByteReader) -> Gen4Events:
    """Événements compilés : quatre listes (compte u32 puis enregistrements) dans l'ordre de event.py."""
    offset = 0

    def records(size: int) -> list[int]:
        nonlocal offset
        count = reader.u32(offset)
        reader.require(offset + 4, count * size)
        starts = [offset + 4 + i * size for i in range(count)]
        offset += 4 + count * size
        return starts

    bg = tuple(_bg(reader, start) for start in records(_BG_SIZE))
    objects = tuple(_object(reader, start) for start in records(_OBJECT_SIZE))
    warps = tuple(_warp(reader, start) for start in records(_WARP_SIZE))
    coords = tuple(CoordEvent(*reader.unpack("8H", start)) for start in records(_COORD_SIZE))
    if offset != len(reader.data):
        raise ValueError(f"{reader.where} : {len(reader.data) - offset} octets après les événements")
    return Gen4Events(index, bg, objects, warps, coords)


def _bg(reader: ByteReader, start: int) -> BgEvent:
    script, kind, x, z, y, facing, padding = reader.unpack("HHiiiHH", start)
    if padding:
        raise ValueError(f"{reader.where} : remplissage non nul à {start:#x}")
    return BgEvent(script, kind, x, z, y, facing)


def _object(reader: ByteReader, start: int) -> ObjectEvent:
    values = reader.unpack("14Hi", start)
    return ObjectEvent(
        local_id=values[0],
        graphics=values[1],
        movement=values[2],
        trainer_type=values[3],
        hidden_flag=values[4],
        script=values[5],
        direction=values[6],
        data=(values[7], values[8], values[9]),
        range_x=values[10],
        range_z=values[11],
        x=values[12],
        z=values[13],
        y=values[14],
    )


def _warp(reader: ByteReader, start: int) -> WarpEvent:
    x, z, header, warp, padding = reader.unpack("HHHHI", start)
    if padding:
        raise ValueError(f"{reader.where} : remplissage non nul à {start:#x}")
    return WarpEvent(x, z, header, warp)


def read_dp_areas(root: Path) -> dict[int, Gen4Area]:
    areas = {}
    for index, path in members(root / FIELD_DATA / "areadata/area_data").items():
        reader = ByteReader(read_binary(path, _AREA_SIZE), str(path))
        if len(reader.data) != _AREA_SIZE:
            raise ValueError(f"{path} : zone de {len(reader.data)} octets, {_AREA_SIZE} attendus")
        areas[index] = Gen4Area(index, *reader.unpack("4H", 0))
    return areas


def read_dp_prop_sets(root: Path) -> dict[int, tuple[int, ...]]:
    """Jeux d'objets posés : u16 nombre de modèles, puis l'indice de chaque modèle dans build_model."""
    sets = {}
    for index, path in members(root / FIELD_DATA / "areadata/area_build_model/area_build").items():
        reader = ByteReader(read_binary(path, _MAX_MEMBER_BYTES), str(path))
        count = reader.u16(0)
        if len(reader.data) != 2 + 2 * count:
            raise ValueError(f"{path} : {count} modèles annoncés pour {len(reader.data)} octets")
        sets[index] = reader.unpack(f"{count}H", 2)
    return sets
