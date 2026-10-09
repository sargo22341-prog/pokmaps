"""Sprites de face GBA, selon les pointeurs graphiques et palettes du moteur."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from .pret_gen3 import Gen3PretRepo
from .pret_gen3_source import read_text, source_path
from .pret_gen3_tilesets import read_palette


def _tables(repo: Gen3PretRepo) -> tuple[dict[str, str], dict[str, dict[str, str]], dict[str, str], str]:
    directory = repo.root / "src/data/object_events"
    pointers = dict(
        re.findall(
            r"\[(OBJ_EVENT_GFX_\w+)\]\s*=\s*&?(\w+)",
            read_text(directory / "object_event_graphics_info_pointers.h"),
        )
    )
    info = {
        name: dict(re.findall(r"\.(width|height|images|paletteTag)\s*=\s*(\w+)", body))
        for name, body in re.findall(
            r"const struct ObjectEventGraphicsInfo (\w+)\s*=\s*\{([^{}]+)\};",
            read_text(directory / "object_event_graphics_info.h"),
            re.S,
        )
    }
    graphics = read_text(directory / "object_event_graphics.h")
    if repo.ruby:
        graphics += read_text(repo.root / "src/field_special_scene.c")
    paths = dict(
        re.findall(
            r'(\w+)\[\]\s*=\s*\w+\("([^"\n]+)"',
            graphics,
        )
    )
    tables = read_text(directory / "object_event_pic_tables.h") + read_text(directory / "berry_tree_graphics_tables.h")
    return pointers, info, paths, tables


def sprite_image(repo: Gen3PretRepo, sprite: str) -> Image.Image:
    pointers, info, paths, tables = _tables(repo)
    if sprite not in pointers or pointers[sprite] not in info:
        raise ValueError(f"{repo.root} : sprite inconnu : {sprite}")
    fields = info[pointers[sprite]]
    table = re.search(rf"\b{fields['images']}\[\]\s*=\s*\{{(.*?)\}};", tables, re.S)
    frame = re.search(r"overworld_frame\((\w+),\s*(\d+),\s*(\d+),\s*(\d+)\)", table[1]) if table else None
    single = re.search(r"obj_frame_tiles\((\w+)\)", table[1]) if table else None
    if not frame and not single:
        raise ValueError(f"{sprite} : première image absente")
    width, height = int(fields["width"]), int(fields["height"])
    index = int(frame[4]) if frame else 0
    name = frame[1] if frame else single[1]
    if frame and (int(frame[2]) * 8, int(frame[3]) * 8) != (width, height):
        raise ValueError(f"{sprite} : dimensions ou image de face incohérentes")
    colors = _sprite_palette(repo, fields["paletteTag"], paths)
    if name not in paths:
        raise ValueError(f"{sprite} : graphisme absent : {name}")
    path = source_path(repo.root, paths[name]).with_suffix(".png")
    with Image.open(path) as source:
        if source.mode != "P" or source.width < width or source.height < height:
            raise ValueError(f"{path} : sprite indexé attendu")
        columns = source.width // width
        left, top = (index % columns) * width, (index // columns) * height
        if top + height > source.height:
            raise ValueError(f"{sprite} : première image hors de la feuille")
        crop = source.crop((left, top, left + width, top + height))
        image = Image.new("RGBA", crop.size)
        pixels = crop.tobytes()
        if max(pixels) > 15:
            raise ValueError(f"{path} : pixels du sprite invalides")
        image.putdata([(*colors[value], 255 if value else 0) for value in pixels])
        return image


def _sprite_palette(repo: Gen3PretRepo, tag: str, paths: dict[str, str]) -> tuple[tuple[int, int, int], ...]:
    text = read_text(repo.root / "src/event_object_movement.c")
    constants = dict(re.findall(r"#define\s+(OBJ_EVENT_PAL_TAG_\w+)\s+(0x[\da-fA-F]+)", text))
    entries = re.findall(r"\{\s*(gObjectEvent\w+),\s*(OBJ_EVENT_PAL_TAG_\w+)\s*\}", text)
    number = int(constants.get(tag, tag), 0)
    matches = [name for name, symbol in entries if int(constants.get(symbol, symbol), 0) == number]
    if len(matches) != 1 or matches[0] not in paths:
        raise ValueError(f"{repo.root} : palette de sprite inconnue : {tag}")
    return read_palette(source_path(repo.root, paths[matches[0]]).with_suffix(".pal"))


def write_sprites(repo: Gen3PretRepo, sprites: set[str], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for sprite in sorted(sprites):
        image = sprite_image(repo, sprite)
        image.save(output / f"{sprite.lower().replace('_', '-')}.webp", "WEBP", lossless=True, method=4)
