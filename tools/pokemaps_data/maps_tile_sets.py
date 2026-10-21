"""Cache d'une pyramide de tuiles complète, sans multiplier les lectures du cache."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

from PIL import Image, features

from .maps_render_cache import RenderCache

_MAX_TILES = 40_000


def tile_set_key(image: Image.Image, geometry: tuple, cache: RenderCache) -> str:
    recipe = (cache.revision, image.mode, image.size, geometry, Image.__version__, features.version("webp"))
    digest = hashlib.sha256(json.dumps(recipe).encode())
    digest.update(image.tobytes())
    return digest.hexdigest()


def restore_tiles(cache: RenderCache, key: str, output: Path) -> int | None:
    content = cache.read(key)
    if content is None:
        return None
    with ZipFile(BytesIO(content)) as archive:
        entries = archive.infolist()
        if len(entries) > _MAX_TILES or sum(entry.file_size for entry in entries) > len(content):
            raise ValueError(f"Cache de carte trop volumineux : {key}")
        folders = set()
        for entry in entries:
            path = Path(entry.filename)
            valid = (
                len(path.parts) == 2
                and path.parts[0].isdecimal()
                and path.suffix == ".webp"
                and len(path.stem.split("_")) == 2
                and all(part.removeprefix("-").isdecimal() for part in path.stem.split("_"))
            )
            if not valid or entry.compress_type != ZIP_STORED or entry.file_size > len(content):
                raise ValueError(f"Tuile de cache invalide : {key} : {entry.filename}")
            destination = output / path
            if destination.parent not in folders:
                destination.parent.mkdir(parents=True, exist_ok=True)
                folders.add(destination.parent)
            destination.write_bytes(archive.read(entry))
    return len(entries)


def store_tiles(cache: RenderCache, key: str, output: Path, paths: list[Path]) -> None:
    if len(paths) > _MAX_TILES:
        raise ValueError(f"Carte trop volumineuse pour le cache : {output}")
    with BytesIO() as buffer:
        with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
            for path in sorted(paths):
                archive.write(path, path.relative_to(output).as_posix())
        cache.write(key, buffer.getvalue())
