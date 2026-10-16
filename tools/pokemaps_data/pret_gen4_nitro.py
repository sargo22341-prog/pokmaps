"""Modèles 3D Nitro (NSBMD : blocs MDL0 et TEX0 facultatif) lus en données pures pour le rendu des cartes.

Formats du Nitro SDK (NNSG3dRes*) tels que les écrivent les deux dépôts ; toute signature, taille ou commande
inconnue arrête la lecture avec le fichier et le décalage. Les textures (TEX0) sont lues par
pret_gen4_textures, les listes d'affichage des formes par pret_gen4_gx.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pret_gen4_nitro_container import blocks, dictionary
from .pret_gen4_source import ByteReader
from .pret_gen4_textures import NitroTextures, read_tex0

FX_ONE = 4096
_MODEL_INFO = 20
_NODE_DICTIONARY = 0x40
# Pivots des rotations compactes (NNSi_G3dGetPivotUtil du Nitro SDK) : indices de la matrice 3 × 3 qui
# reçoivent A, B, ±B et ±A.
_PIVOTS = (
    (4, 5, 7, 8),
    (3, 5, 6, 8),
    (3, 4, 6, 7),
    (1, 2, 7, 8),
    (0, 2, 6, 8),
    (0, 1, 6, 7),
    (1, 2, 4, 5),
    (0, 2, 3, 5),
    (0, 1, 3, 4),
)
_MATERIAL_TEXTURE_MATRIX = 0x1
_MATERIAL_SCALE_ONE = 0x2
_MATERIAL_ROTATION_ZERO = 0x4
_MATERIAL_TRANSLATION_ZERO = 0x8
_MATERIAL_EFFECT_MATRIX = 0x2000
# Commandes de rendu (SBC) : nombre d'octets d'arguments, sans compter ceux des drapeaux de pile.
_SBC_RET, _SBC_NODEMIX, _SBC_CALLDL = 0x01, 0x09, 0x0A
_SBC_ARGUMENTS = {
    0x00: 0,
    0x01: 0,
    0x02: 2,
    0x03: 1,
    0x04: 1,
    0x05: 1,
    0x06: 3,
    0x07: 1,
    0x08: 1,
    0x0B: 0,
    0x0C: 2,
    0x0D: 2,
}
# Commandes qui lisent ou rangent une matrice de pile selon leurs drapeaux (bits 5 et 6 de l'opcode).
_SBC_STACK = frozenset({0x06, 0x07, 0x08})


@dataclass(frozen=True)
class NitroNode:
    name: str
    translation: tuple[int, int, int]
    rotation: tuple[int, ...]  # matrice 3 × 3 ligne par ligne, fx16
    scale: tuple[int, int, int]


@dataclass(frozen=True)
class NitroMaterial:
    name: str
    diffuse_ambient: int
    specular_emission: int
    polygon_attributes: int
    texture_parameters: int
    flags: int
    original_size: tuple[int, int]
    texture_scale: tuple[int, int]
    texture_rotation: tuple[int, int]  # (sinus, cosinus) fx16
    texture_translation: tuple[int, int]
    texture: str | None
    palette: str | None


@dataclass(frozen=True)
class NitroShape:
    name: str
    flags: int
    display_list: bytes


@dataclass(frozen=True)
class SbcCommand:
    opcode: int
    flags: int
    arguments: tuple[int, ...]


@dataclass(frozen=True)
class NitroModel:
    name: str
    position_scale: int
    inverse_position_scale: int
    box: tuple[int, ...]  # x, y, z, largeur, hauteur, profondeur (fx16), puis échelle et inverse de la boîte
    nodes: tuple[NitroNode, ...]
    materials: tuple[NitroMaterial, ...]
    shapes: tuple[NitroShape, ...]
    render: tuple[SbcCommand, ...]


@dataclass(frozen=True)
class NitroFile:
    models: tuple[NitroModel, ...]
    textures: NitroTextures | None


def read_nsbmd(data: bytes, where: str) -> NitroFile:
    reader = ByteReader(data, where)
    found = blocks(reader, b"BMD0")
    if b"MDL0" not in found or set(found) - {b"MDL0", b"TEX0"}:
        raise ValueError(f"{where} : blocs NSBMD inattendus : {sorted(found)}")
    mdl0 = found[b"MDL0"]
    models = tuple(_model(reader, mdl0 + reader.u32(entry), name) for name, entry in dictionary(reader, mdl0 + 8))
    textures = read_tex0(reader, found[b"TEX0"]) if b"TEX0" in found else None
    return NitroFile(models, textures)


def _model(reader: ByteReader, start: int, name: str) -> NitroModel:
    size, sbc, materials, shapes = reader.unpack("4I", start)
    reader.require(start, size)
    info = start + _MODEL_INFO
    node_count, material_count, shape_count = reader.unpack("3B", info + 3)
    nodes = tuple(
        _node(reader, start + _NODE_DICTIONARY + reader.u32(entry), node_name)
        for node_name, entry in dictionary(reader, start + _NODE_DICTIONARY)
    )
    model = NitroModel(
        name=name,
        position_scale=reader.s32(info + 8),
        inverse_position_scale=reader.s32(info + 12),
        box=(*reader.unpack("6h", info + 24), *reader.unpack("2i", info + 36)),
        nodes=nodes,
        materials=_materials(reader, start + materials),
        shapes=_shapes(reader, start + shapes),
        render=_sbc(reader, start + sbc, start + materials),
    )
    if (len(model.nodes), len(model.materials), len(model.shapes)) != (node_count, material_count, shape_count):
        raise ValueError(f"{reader.where} : {name} : nombres de nœuds, matériaux ou formes incohérents")
    return model


def _node(reader: ByteReader, offset: int, name: str) -> NitroNode:
    flag, m00 = reader.u16(offset), reader.s16(offset + 2)
    position = offset + 4
    translation = (0, 0, 0)
    if not flag & 0x1:
        translation = reader.unpack("3i", position)
        position += 12
    rotation: tuple[int, ...] = (FX_ONE, 0, 0, 0, FX_ONE, 0, 0, 0, FX_ONE)
    if not flag & 0x2:
        if flag & 0x8:
            rotation = _pivot_rotation(flag, *reader.unpack("2h", position))
            position += 4
        else:
            rotation = (m00, *reader.unpack("8h", position))
            position += 16
    scale = (FX_ONE, FX_ONE, FX_ONE)
    if not flag & 0x4:
        scale = reader.unpack("3i", position)
    return NitroNode(name, translation, rotation, scale)


def _pivot_rotation(flag: int, a: int, b: int) -> tuple[int, ...]:
    pivot = (flag >> 4) & 0xF
    if pivot >= len(_PIVOTS):
        raise ValueError(f"pivot de rotation inconnu : {pivot}")
    matrix = [0] * 9
    matrix[pivot] = -FX_ONE if flag & 0x100 else FX_ONE
    first, second, third, fourth = _PIVOTS[pivot]
    matrix[first], matrix[second] = a, b
    matrix[third] = -b if flag & 0x200 else b
    matrix[fourth] = -a if flag & 0x400 else a
    return tuple(matrix)


def _materials(reader: ByteReader, base: int) -> tuple[NitroMaterial, ...]:
    entries = dictionary(reader, base + 4)
    textures = _bindings(reader, base, base + reader.u16(base), len(entries))
    palettes = _bindings(reader, base, base + reader.u16(base + 2), len(entries))
    return tuple(
        _material(reader, base + reader.u32(entry), name, textures.get(i), palettes.get(i))
        for i, (name, entry) in enumerate(entries)
    )


def _bindings(reader: ByteReader, base: int, offset: int, materials: int) -> dict[int, str]:
    """Texture ou palette de chaque matériau, d'après le dictionnaire nom -> liste de matériaux."""
    bound: dict[int, str] = {}
    for name, entry in dictionary(reader, offset):
        start, count = reader.u16(entry), reader.u8(entry + 2)
        for material in reader.slice(base + start, count):
            if material >= materials or material in bound:
                raise ValueError(f"{reader.where} : liaison {name} vers le matériau {material} invalide")
            bound[material] = name
    return bound


def _material(reader: ByteReader, offset: int, name: str, texture: str | None, palette: str | None) -> NitroMaterial:
    diffuse, specular, polygon, _, texture_parameters = reader.unpack("5I", offset + 4)
    flags, width, height = reader.unpack("3H", offset + 0x1E)
    position = offset + 0x2C
    scale, rotation, translation = (FX_ONE, FX_ONE), (0, FX_ONE), (0, 0)
    if flags & _MATERIAL_TEXTURE_MATRIX:
        if not flags & _MATERIAL_SCALE_ONE:
            scale = reader.unpack("2i", position)
            position += 8
        if not flags & _MATERIAL_ROTATION_ZERO:
            rotation = reader.unpack("2h", position)
            position += 4
        if not flags & _MATERIAL_TRANSLATION_ZERO:
            translation = reader.unpack("2i", position)
    if flags & _MATERIAL_EFFECT_MATRIX:
        raise ValueError(f"{reader.where} : matériau {name} à matrice d'effet non prise en charge")
    return NitroMaterial(
        name,
        diffuse,
        specular,
        polygon,
        texture_parameters,
        flags,
        (width, height),
        scale,
        rotation,
        translation,
        texture,
        palette,
    )


def _shapes(reader: ByteReader, base: int) -> tuple[NitroShape, ...]:
    shapes = []
    for name, entry in dictionary(reader, base):
        start = base + reader.u32(entry)
        flags, list_offset, list_size = reader.unpack("3I", start + 4)
        shapes.append(NitroShape(name, flags, reader.slice(start + list_offset, list_size)))
    return tuple(shapes)


def _sbc(reader: ByteReader, start: int, end: int) -> tuple[SbcCommand, ...]:
    """Commandes de rendu jusqu'à RET ; les octets après RET (alignement) doivent être nuls."""
    commands = []
    position = start
    while position < end:
        opcode, flags = reader.u8(position) & 0x1F, reader.u8(position) >> 5
        position += 1
        if opcode == _SBC_NODEMIX:
            count = reader.u8(position + 1)
            size = 2 + 3 * count
        elif opcode == _SBC_CALLDL:
            size = 8
        elif opcode in _SBC_ARGUMENTS:
            size = _SBC_ARGUMENTS[opcode] + (bin(flags & 0x3).count("1") if opcode in _SBC_STACK else 0)
        else:
            raise ValueError(f"{reader.where} : commande de rendu inconnue {opcode:#x} à {position - 1:#x}")
        commands.append(SbcCommand(opcode, flags, tuple(reader.slice(position, size))))
        position += size
        if opcode == _SBC_RET:
            if any(reader.slice(position, end - position)):
                raise ValueError(f"{reader.where} : octets non nuls après la fin des commandes de rendu")
            return tuple(commands)
    raise ValueError(f"{reader.where} : commandes de rendu sans RET")
