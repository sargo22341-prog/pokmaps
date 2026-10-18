"""Poses de face des personnages DS, lues séparément dans chaque dépôt."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .pret_gen4 import Gen4PretRepo
from .pret_gen4_maps_dp import _labelled_bytes
from .pret_gen4_narc import members
from .pret_gen4_source import ByteReader, metang_enum, read_binary, read_text
from .pret_gen4_textures import decode, read_nsbtx


@dataclass(frozen=True)
class FieldSprite:
    graphics: int
    source: str
    image: Image.Image


def platinum_sprite_files(repo: Gen4PretRepo) -> dict[int, Path]:
    graphics = metang_enum(repo.root / "generated/object_events_gfx.txt")
    source = read_text(repo.root / "src/overlay005/object_event_gfx_data.c")
    body = source.split("gObjectEventGfxTexturesTable[] = {", 1)[1].split("};", 1)[0]
    entries = re.findall(r"\{\s*(OBJ_EVENT_GFX_\w+),\s*(\w+)_nsbtx\s*\}", body)
    needed = {name for _, name in entries}
    folder = repo.root / "res/graphics/field_sprites"
    pngs: dict[str, Path] = {}
    for path in sorted(folder.rglob("*.png")):
        if path.stem not in needed:
            continue
        if path.stem in pngs:
            raise ValueError(f"{folder} : PNG ambigu : {path.stem}")
        pngs[path.stem] = path
    result = {}
    for constant, name in entries:
        if name in pngs:
            result[graphics[constant]] = pngs[name]
    if not result:
        raise ValueError(f"{repo.root} : table des sprites PNG vide")
    return result


def diamond_sprite_files(repo: Gen4PretRepo) -> dict[int, Path]:
    path = repo.root / "arm9/overlays/05/asm/ov05_021F0514.s"
    data = _labelled_bytes(path, "ov05_021FA0AC")
    reader = ByteReader(data, str(path))
    if len(data) % 8:
        raise ValueError(f"{path} : table des sprites non alignée")
    files = members(repo.root / "files/data/mmodel/mmodel")
    result = {}
    for offset in range(0, len(data), 8):
        graphics, member = reader.unpack("2I", offset)
        if graphics == 0xFFFF:
            break
        if graphics in result or member not in files:
            raise ValueError(f"{path} : sprite {graphics} ou archive {member} invalide")
        result[graphics] = files[member]
    if not result or graphics != 0xFFFF:
        raise ValueError(f"{path} : table des sprites sans terminaison")
    return result


def read_field_sprites(repo: Gen4PretRepo, used: set[int]) -> tuple[FieldSprite, ...]:
    files = platinum_sprite_files(repo) if repo.platinum else diamond_sprite_files(repo)
    result = []
    for graphics in sorted(used & files.keys()):
        path = files[graphics]
        image = _png_frame(repo, path) if repo.platinum else _nitro_frame(path)
        result.append(FieldSprite(graphics, path.relative_to(repo.root).as_posix(), image))
    return tuple(result)


def _png_frame(repo: Gen4PretRepo, path: Path) -> Image.Image:
    folder = repo.root / "res/graphics/field_sprites"
    build = read_text(folder / "meson.build")
    relative = path.relative_to(folder).as_posix()
    categories = re.findall(r"field_sprites_textures_(\w+) = \[(.*?)\]", build, re.DOTALL)
    category = next((name for name, body in categories if f"'{relative}'" in body), None)
    with Image.open(path) as source:
        if source.width > 256 or source.height > 4096:
            raise ValueError(f"{path} : planche de personnage inattendue : {source.size}")
        if category == "two_frame_pokemon":
            if source.height % 2:
                raise ValueError(f"{path} : planche à deux images de hauteur impaire")
            height = source.height // 2
        elif category and "single_frame" in category:
            height = source.height
        else:
            height = min(32, source.height)
        # Les planches de marche commencent par quatre images de dos, puis quatre de face.
        top = 4 * height if source.height >= 16 * height else 0
        image = source.convert("RGBA").crop((0, top, source.width, top + height))
        # Le PNG garde une couleur invisible sous l'alpha nul ; le décodeur Nitro rend du noir transparent.
        data = bytes(value for pixel in image.get_flattened_data() for value in (pixel if pixel[3] else (0, 0, 0, 0)))
        return Image.frombytes("RGBA", image.size, data)


def _nitro_frame(path: Path) -> Image.Image:
    textures = read_nsbtx(read_binary(path), str(path))
    if not textures.textures:
        raise ValueError(f"{path} : personnage sans texture")
    # Les dictionnaires Nitro sont triés lexicalement : .10 précède .2 ; la face commence au cinquième cadre.
    names = sorted(
        textures.textures, key=lambda key: (int(key.rsplit(".", 1)[1]) if key.rsplit(".", 1)[-1].isdigit() else 0, key)
    )
    name = names[4] if len(names) >= 16 else names[0]
    texture = textures.textures[name]
    prefix = name.rsplit(".", 1)[0]
    palette = textures.palettes.get(prefix) or textures.palettes.get(name + "_pl")
    if palette is None and len(textures.palettes) == 1:
        palette = next(iter(textures.palettes.values()))
    pixels = decode(texture, palette)
    data = bytes((component << 3) | (component >> 2) for pixel in pixels for component in pixel)
    return Image.frombytes("RGBA", (texture.width, texture.height), data)
