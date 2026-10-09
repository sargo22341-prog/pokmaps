"""Première image des animations GBA, aux adresses VRAM données par le moteur."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from .pret_gen3 import Gen3PretRepo
from .pret_gen3_source import read_text, source_path
from .pret_gen3_tilesets import Gen3Tileset


def _functions(text: str) -> dict[str, str]:
    result = {}
    for match in re.finditer(r"(?:static\s+)?void\s+(\w+)\([^;{}]*\)\s*\{", text):
        depth = 1
        for index in range(match.end(), len(text)):
            depth += (text[index] == "{") - (text[index] == "}")
            if depth == 0:
                result[match[1]] = text[match.end() : index]
                break
        else:
            raise ValueError(f"Animation : fonction tronquée : {match[1]}")
    return result


def _reachable(functions: dict[str, str], callback: str) -> str:
    if callback not in functions:
        raise ValueError(f"Animation : callback inconnu : {callback}")
    pending = {callback}
    visited: set[str] = set()
    for _ in range(len(functions)):
        if not pending:
            break
        name = min(pending)
        pending.remove(name)
        visited.add(name)
        references = re.findall(r"\b(\w+)\s*(?:\(|;)", functions[name])
        pending.update(reference for reference in references if reference in functions and reference not in visited)
    if pending:
        raise ValueError(f"Animation : parcours trop long : {callback}")
    return "\n".join(functions[name] for name in functions if name in visited)


def _destinations(expression: str, text: str, ruby: bool) -> tuple[int, ...]:
    macro = r"BG_TILE_ADDR\((\d+)\)" if ruby else r"TILE_OFFSET_4BPP\(([^)]+)\)"
    if match := re.search(r"(\w+)\[", expression):
        table = re.search(rf"\b{match[1]}\[\]\s*=\s*\{{(.*?)\}};", text, re.S)
        if not table:
            raise ValueError(f"Animation : adresses absentes : {expression}")
        expression = table[1]
    values = re.findall(macro, expression)
    if ruby and not values:
        addresses = re.findall(r"VRAM\s*\+\s*(0x[\da-fA-F]+)", expression)
        if addresses:
            return tuple(int(address, 0) // 32 for address in addresses)
    result = []
    for value in values:
        value = value.replace("NUM_TILES_IN_PRIMARY", "512")
        if not re.fullmatch(r"[\d\s+]+", value):
            raise ValueError(f"Animation : adresse inconnue : {value}")
        result.append(sum(int(part.strip()) for part in value.split("+")) * (4 if ruby else 1))
    if not result:
        raise ValueError(f"Animation : destination inconnue : {expression}")
    return tuple(result)


def _frame(root: Gen3PretRepo, text: str, table: str, count: int) -> tuple[bytes, ...]:
    declaration = re.search(rf"\b{table}\[\]\s*=\s*\{{\s*(\w+)", text)
    if not declaration:
        raise ValueError(f"Animation : table absente : {table}")
    source = re.search(rf"\b{declaration[1]}\[\]\s*=\s*\w+\(([^;]+)\);", text)
    if not source:
        raise ValueError(f"Animation : image absente : {declaration[1]}")
    paths = [
        source_path(root.root, value).with_suffix(".png")
        for value in re.findall(r'"([^"\n]+)"', source[1])
        if "/" in value
    ]
    frames = tuple(pixels for path in paths for pixels in _image_tiles(path))
    if len(frames) < count:
        raise ValueError(f"{declaration[1]} : image d’animation trop courte")
    return frames[:count]


def _image_tiles(path: Path) -> tuple[bytes, ...]:
    with Image.open(path) as image:
        if image.mode != "P" or image.width % 8 or image.height % 8 or image.width * image.height > 65536:
            raise ValueError(f"{path} : image d’animation invalide")
        raw = image.tobytes()
        if max(raw) > 15:
            raise ValueError(f"{path} : pixels d’animation invalides")
        columns = image.width // 8
        return tuple(
            bytes(
                raw[((number // columns) * 8 + y) * image.width + (number % columns) * 8 + x]
                for y in range(8)
                for x in range(8)
            )
            for number in range(len(raw) // 64)
        )


def animation_tiles(repo: Gen3PretRepo, tileset: Gen3Tileset) -> dict[int, bytes]:
    if tileset.animation_callback in {"NULL", "0"}:
        return {}
    path = repo.root / ("src/tileset_anim.c" if repo.ruby else "src/tileset_anims.c")
    text = read_text(path)
    body = _reachable(_functions(text), tileset.animation_callback)
    call = "QueueTilesetAnimDma" if repo.ruby else "AppendTilesetAnimToBuffer"
    entries = re.findall(rf"{call}\((\w+)\[[^\]]+\],\s*(.*?),\s*([^,;]+)\);", body)
    if body.count(f"{call}(") != len(entries):
        raise ValueError(f"{tileset.const} : appel d’animation non pris en charge")
    result: dict[int, bytes] = {}
    for table, destination, size in entries:
        if repo.ruby:
            count, remainder = divmod(int(size, 0), 32)
        else:
            match = re.fullmatch(r"(\d+)\s*\*\s*TILE_SIZE_4BPP", size.strip())
            if not match:
                raise ValueError(f"{tileset.const} : taille d’animation inconnue : {size}")
            count, remainder = int(match[1]), 0
        if remainder or not 0 < count <= 128:
            raise ValueError(f"{tileset.const} : taille d’animation invalide")
        frame = _frame(repo, text, table, count)
        for start in _destinations(destination, text, repo.ruby):
            for offset, pixels in enumerate(frame):
                # Les variantes B de Lavandia remplacent l'image après plusieurs tours ; garder la première.
                result.setdefault(start + offset, pixels)
    return result
