"""Empreinte des seules entrées qui déterminent les pixels d'un cadre DS."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

from .maps_raster_gen4 import RasterTexture
from .maps_render_cache import RenderCache

if TYPE_CHECKING:
    from .maps_render_gen4 import RasterTriangle
    from .maps_tiles_gen4 import BlockSource, TileJob


@dataclass(frozen=True)
class FrameCache:
    storage: RenderCache
    revision: str

    @classmethod
    def for_sources(cls, root: Path) -> FrameCache:
        digest = hashlib.sha256()
        for name in ("maps_raster_gen4.py", "maps_tiles_gen4.py", "maps_frame_cache_gen4.py"):
            digest.update(Path(__file__).with_name(name).read_text(encoding="utf-8").encode())
        return cls(RenderCache(root.parent / "map-renders/frames"), digest.hexdigest())

    def read(self, key: str) -> Image.Image | None:
        content = self.storage.read(key)
        if content is None:
            return None
        with Image.open(BytesIO(content)) as image:
            return image.convert("RGBA")

    def write(self, key: str, image: Image.Image) -> None:
        with BytesIO() as buffer:
            image.save(buffer, "PNG", compress_level=1)
            self.storage.write(key, buffer.getvalue())

    def key(self, job: TileJob, prepared: list[tuple[BlockSource, tuple[RasterTriangle, ...]]]) -> str:
        digest = hashlib.sha256(self.revision.encode())
        digest.update(repr((job.origin, job.size, job.ceiling)).encode())
        textures: dict[int, str] = {}
        for source, triangles in prepared:
            digest.update(repr((source.offset, source.request.cotangent, source.request.ceiling)).encode())
            for vertices, material in triangles:
                texture = material.texture
                if texture is not None and id(texture) not in textures:
                    textures[id(texture)] = _texture_key(texture)
                values = (
                    tuple((v.position, v.texcoord, v.color) for v in vertices),
                    material.alpha,
                    material.faces,
                    None if texture is None else textures[id(texture)],
                )
                digest.update(json.dumps(values, separators=(",", ":")).encode())
        return digest.hexdigest()


def _texture_key(texture: RasterTexture) -> str:
    source = texture.source
    digest = hashlib.sha256(repr((source.width, source.height, source.repeat, source.flip)).encode())
    digest.update(bytes(channel for pixel in texture.pixels for channel in pixel))
    return digest.hexdigest()
