"""Textures et palettes Nitro (bloc TEX0 des NSBTX et NSBMD), décodées en couleurs RGBA 5 bits.

Disposition du bloc (Nitro SDK, NNSG3dResTex) : informations des textures à 0x08, des palettes à 0x2C ;
dictionnaires des textures (8 octets par entrée : paramètres TEXIMAGE_PARAM puis taille d'origine) et des
palettes (décalage en pas de 8 octets). Les cartes, objets et PNJ des deux dépôts n'emploient que cinq formats :
les textures compressées 4 × 4 et directes sont refusées explicitement.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pret_gen4_nitro_container import blocks, dictionary
from .pret_gen4_source import ByteReader

# Formats GX_TEXFMT_* employés : bits par texel. 5 (4 × 4 compressé) et 7 (direct) n'apparaissent pas.
A3I5, PALETTE_4, PALETTE_16, PALETTE_256, A5I3 = 1, 2, 3, 4, 6
_BITS = {A3I5: 8, PALETTE_4: 2, PALETTE_16: 4, PALETTE_256: 8, A5I3: 8}
_PALETTE_FORMATS = frozenset({PALETTE_4, PALETTE_16, PALETTE_256})
OPAQUE = 31
Rgba = tuple[int, int, int, int]
_TRANSPARENT: Rgba = (0, 0, 0, 0)


@dataclass(frozen=True)
class Texture:
    name: str
    width: int
    height: int
    format: int
    color0_transparent: bool
    repeat: tuple[bool, bool]
    flip: tuple[bool, bool]
    texels: bytes


@dataclass(frozen=True)
class Palette:
    name: str
    colors: tuple[int, ...]  # RGB555


@dataclass(frozen=True)
class NitroTextures:
    textures: dict[str, Texture]
    palettes: dict[str, Palette]


def read_tex0(reader: ByteReader, start: int) -> NitroTextures:
    if reader.slice(start, 4) != b"TEX0":
        raise ValueError(f"{reader.where} : bloc TEX0 attendu à {start:#x}")
    texture_data = start + reader.u32(start + 0x14)
    if reader.u16(start + 0x1C):
        raise ValueError(f"{reader.where} : textures compressées 4 × 4 non prises en charge")
    palette_size = reader.u16(start + 0x30) << 3
    palette_data = start + reader.u32(start + 0x38)
    reader.require(palette_data, palette_size)
    textures = {}
    for name, entry in dictionary(reader, start + reader.u16(start + 0x0E)):
        textures[name] = _texture(reader, name, reader.u32(entry), texture_data)
    entries = [(name, reader.u16(entry) << 3) for name, entry in dictionary(reader, start + reader.u16(start + 0x34))]
    bounds = sorted({offset for _, offset in entries} | {palette_size})
    palettes = {}
    for name, offset in entries:
        if offset >= palette_size:
            raise ValueError(f"{reader.where} : palette {name} hors des données")
        end = bounds[bounds.index(offset) + 1]
        palettes[name] = Palette(name, reader.unpack(f"{(end - offset) // 2}H", palette_data + offset))
    return NitroTextures(textures, palettes)


def _texture(reader: ByteReader, name: str, parameters: int, data: int) -> Texture:
    offset = (parameters & 0xFFFF) << 3
    width, height = 8 << ((parameters >> 20) & 7), 8 << ((parameters >> 23) & 7)
    texture_format = (parameters >> 26) & 7
    if texture_format not in _BITS:
        raise ValueError(f"{reader.where} : texture {name} de format {texture_format} non pris en charge")
    texels = reader.slice(data + offset, width * height * _BITS[texture_format] // 8)
    return Texture(
        name=name,
        width=width,
        height=height,
        format=texture_format,
        color0_transparent=bool(parameters >> 29 & 1),
        repeat=(bool(parameters >> 16 & 1), bool(parameters >> 17 & 1)),
        flip=(bool(parameters >> 18 & 1), bool(parameters >> 19 & 1)),
        texels=texels,
    )


def rgb555(color: int) -> tuple[int, int, int]:
    return color & 31, (color >> 5) & 31, (color >> 10) & 31


def decode(texture: Texture, palette: Palette | None) -> tuple[Rgba, ...]:
    """Texels ligne par ligne en (rouge, vert, bleu, alpha) sur 5 bits ; un indice hors de la palette arrête."""
    if palette is None:
        raise ValueError(f"texture {texture.name} sans palette")
    if texture.format in _PALETTE_FORMATS:
        return _decode_indexed(texture, palette)
    return _decode_alpha(texture, palette)


def _color(palette: Palette, index: int, texture: Texture) -> tuple[int, int, int]:
    if index >= len(palette.colors):
        raise ValueError(f"texture {texture.name} : couleur {index} hors de la palette {palette.name}")
    return rgb555(palette.colors[index])


def _decode_indexed(texture: Texture, palette: Palette) -> tuple[Rgba, ...]:
    bits = _BITS[texture.format]
    mask, per_byte = (1 << bits) - 1, 8 // bits
    pixels = []
    for i in range(texture.width * texture.height):
        index = (texture.texels[i // per_byte] >> ((i % per_byte) * bits)) & mask
        if index == 0 and texture.color0_transparent:
            pixels.append(_TRANSPARENT)
        else:
            pixels.append((*_color(palette, index, texture), OPAQUE))
    return tuple(pixels)


def _decode_alpha(texture: Texture, palette: Palette) -> tuple[Rgba, ...]:
    """A3I5 (alpha 3 bits étendu à 5) et A5I3."""
    pixels = []
    for value in texture.texels:
        if texture.format == A3I5:
            alpha = value >> 5
            pixels.append((*_color(palette, value & 31, texture), alpha * 4 + alpha // 2))
        else:
            pixels.append((*_color(palette, value & 7, texture), value >> 3))
    return tuple(pixels)


def read_nsbtx(data: bytes, where: str) -> NitroTextures:
    # Un jeu de textures d'objets vide est un membre de quatre octets nuls (Diamant/Perle).
    if data == bytes(4):
        return NitroTextures({}, {})
    reader = ByteReader(data, where)
    found = blocks(reader, b"BTX0")
    if set(found) != {b"TEX0"}:
        raise ValueError(f"{where} : blocs NSBTX inattendus : {sorted(found)}")
    return read_tex0(reader, found[b"TEX0"])
