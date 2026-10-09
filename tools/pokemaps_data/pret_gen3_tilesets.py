"""Tilesets GBA : pixels indexés, palettes, descripteurs et attributs des métatuiles."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .pret_gen3_source import MAX_SOURCE_BYTES, conditional_text, initializer_fields, read_text, source_path


@dataclass(frozen=True)
class Gen3Metatile:
    tiles: tuple[int, ...]
    behavior: int
    layer_type: int
    terrain: int | None
    encounter_type: int | None


@dataclass(frozen=True)
class Gen3Tileset:
    const: str
    secondary: bool
    tile_count: int
    pixels: bytes
    image_width: int
    palettes: tuple[tuple[tuple[int, int, int], ...], ...]
    metatiles: tuple[Gen3Metatile, ...]
    primary_tile_count: int
    primary_metatile_count: int
    primary_palette_count: int
    compressed: bool
    animation_callback: str


def read_palette(path: Path) -> tuple[tuple[int, int, int], ...]:
    lines = read_text(path).splitlines()
    if lines[:3] != ["JASC-PAL", "0100", "16"] or len(lines) != 19:
        raise ValueError(f"{path} : palette JASC de 16 couleurs attendue")
    colors = tuple(tuple(int(value) for value in line.split()) for line in lines[3:])
    if any(len(color) != 3 or any(not 0 <= value <= 255 for value in color) for color in colors):
        raise ValueError(f"{path} : couleur invalide")
    return colors


def _pixels(path: Path) -> tuple[bytes, int, int]:
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"{path} : image trop volumineuse")
    with Image.open(path) as image:
        if image.mode != "P" or image.width % 8 or image.height % 8 or image.width * image.height > 1024 * 1024:
            raise ValueError(f"{path} : image 4 bpp indexée attendue")
        pixels = image.tobytes()
        if max(pixels) > 15:
            raise ValueError(f"{path} : indice supérieur à 15")
        return pixels, image.width, image.width * image.height // 64


def _metatiles(tile_path: Path, attr_path: Path, remake: bool) -> tuple[Gen3Metatile, ...]:
    directory = tile_path.parent
    count, rest = divmod(tile_path.stat().st_size, 16)
    size = 4 if remake else 2
    if rest or not 0 < count <= 1024 or attr_path.stat().st_size != count * size:
        raise ValueError(f"{directory} : métatuiles ou attributs incohérents")
    tiles = struct.unpack(f"<{count * 8}H", tile_path.read_bytes())
    attributes = struct.unpack(f"<{count}{'I' if remake else 'H'}", attr_path.read_bytes())
    result = []
    for index, attribute in enumerate(attributes):
        behavior = attribute & (0x1FF if remake else 0xFF)
        layer = (attribute >> (29 if remake else 12)) & (3 if remake else 15)
        if layer > 2:
            raise ValueError(f"{directory} : couche inconnue {layer}")
        result.append(
            Gen3Metatile(
                tiles[index * 8 : index * 8 + 8],
                behavior,
                layer,
                (attribute >> 9) & 31 if remake else None,
                (attribute >> 24) & 7 if remake else None,
            )
        )
    return tuple(result)


@dataclass(frozen=True)
class _TilesetHeader:
    secondary: bool
    compressed: bool
    tiles: str
    palettes: str
    metatiles: str
    attributes: str
    callback: str


def _headers(root: Path, ruby: bool) -> dict[str, _TilesetHeader]:
    path = root / ("data/tilesets/headers.inc" if ruby else "src/data/tilesets/headers.h")
    text = conditional_text(path, frozenset({"ENGLISH", "RUBY" if ruby else "EMERALD"}))
    result = {}
    if ruby:
        entries = re.findall(r"(gTileset_\w+)::(.*?)(?=gTileset_\w+::|\Z)", text, re.S)
        for name, body in entries:
            values = re.findall(r"\.(?:byte|2byte|4byte)\s+(\w+)", body)
            if len(values) != 8 or any(value not in {"TRUE", "FALSE"} for value in values[:2]) or values[2] != "0":
                raise ValueError(f"{path} : en-tête invalide {name}")
            result[name] = _TilesetHeader(values[1] == "TRUE", values[0] == "TRUE", *values[3:])
    else:
        entries = re.findall(r"const struct Tileset (gTileset_\w+)\s*=\s*\{([^{}]+)\};", text, re.S)
        declarations = re.findall(r"const struct Tileset (gTileset_\w+)\s*=", text)
        if len(declarations) != len(entries):
            raise ValueError(f"{path} : initialiseur de tileset non pris en charge")
        for name, body in entries:
            fields = initializer_fields(body, path, name)
            expected = {
                "isCompressed",
                "isSecondary",
                "tiles",
                "palettes",
                "metatiles",
                "metatileAttributes",
                "callback",
            }
            if fields.keys() != expected or any(
                fields[key] not in {"TRUE", "FALSE"} for key in ("isCompressed", "isSecondary")
            ):
                raise ValueError(f"{path} : en-tête invalide {name}")
            result[name] = _TilesetHeader(
                fields["isSecondary"] == "TRUE",
                fields["isCompressed"] == "TRUE",
                fields["tiles"],
                fields["palettes"],
                fields["metatiles"],
                fields["metatileAttributes"],
                fields["callback"],
            )
    if not result or len(result) != len(entries) or len(result) > 128:
        raise ValueError(f"{path} : tilesets absents, répétés ou trop nombreux")
    return result


def _asset_paths(root: Path, ruby: bool) -> dict[str, str]:
    files = (
        ["src/data/graphics.c", "data/tilesets/graphics.inc", "data/tilesets/metatiles.inc"]
        if ruby
        else ["src/graphics.c", "src/data/tilesets/graphics.h", "src/data/tilesets/metatiles.h"]
    )
    result: dict[str, str] = {}
    for relative in files:
        text = conditional_text(root / relative, frozenset({"ENGLISH", "RUBY" if ruby else "EMERALD"}))
        result.update(
            re.findall(
                r"(g(?:TilesetTiles|TilesetPalettes|Metatiles|MetatileAttributes)_\w+)"
                r'\[.*?\]\s*=\s*(?:\{\s*)?\w+\("([^"\n]+)"',
                text,
                re.S,
            )
        )
        result.update(
            re.findall(
                r"(g(?:TilesetTiles|TilesetPalettes|Metatiles|MetatileAttributes)_\w+)"
                r'::\s*\.incbin\s+"([^"]+)"',
                text,
            )
        )
    return result


def read_tilesets(root: Path, ruby: bool, remake: bool) -> dict[str, Gen3Tileset]:
    paths = _asset_paths(root, ruby)
    result = {}
    for name, header in _headers(root, ruby).items():
        tiles, palette, metatiles, attributes = header.tiles, header.palettes, header.metatiles, header.attributes
        if any(reference not in paths for reference in (tiles, palette, metatiles, attributes)):
            raise ValueError(f"{root} : asset absent pour {name}")
        image_path = source_path(root, paths[tiles]).with_name("tiles.png")
        pixels, width, count = _pixels(image_path)
        palette_dir = source_path(root, paths[palette]).parent
        palettes = tuple(read_palette(palette_dir / f"{index:02d}.pal") for index in range(16))
        result[name] = Gen3Tileset(
            name,
            header.secondary,
            count,
            pixels,
            width,
            palettes,
            _metatiles(source_path(root, paths[metatiles]), source_path(root, paths[attributes]), remake),
            640 if remake else 512,
            640 if remake else 512,
            7 if remake else 6,
            header.compressed,
            header.callback,
        )
    return result


def map_palettes(primary: Gen3Tileset, secondary: Gen3Tileset) -> tuple[tuple[tuple[int, int, int], ...], ...]:
    """Palettes de carte 0 à 12 ; les palettes 13 à 15 sont réservées aux objets du moteur."""
    if primary.secondary or not secondary.secondary or primary.primary_palette_count != secondary.primary_palette_count:
        raise ValueError(f"{primary.const}/{secondary.const} : paire de tilesets incompatible")
    split = primary.primary_palette_count
    return primary.palettes[:split] + secondary.palettes[split:13]
