"""Cache de rendus adressé par leur contenu, avec intégrité et publication atomique."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

_MAX_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class RenderCache:
    root: Path
    revision: str = ""

    @classmethod
    def for_tiles(cls, root: Path) -> RenderCache:
        digest = hashlib.sha256()
        for name in ("maps_render.py", "maps_render_cache.py", "maps_tile_sets.py"):
            digest.update(Path(__file__).with_name(name).read_text(encoding="utf-8").encode())
        return cls(root, digest.hexdigest())

    def read(self, key: str) -> bytes | None:
        path = self.root / key[:2] / key
        if not path.is_file():
            return None
        if path.stat().st_size > _MAX_BYTES:
            raise ValueError(f"Cache de rendu trop volumineux : {path}")
        digest, separator, content = path.read_bytes().partition(b"\n")
        if not separator or hashlib.sha256(content).hexdigest().encode() != digest:
            raise ValueError(f"Cache de rendu corrompu : {path}")
        return content

    def write(self, key: str, content: bytes) -> None:
        if len(content) + 65 > _MAX_BYTES:
            raise ValueError(f"Rendu trop volumineux pour le cache : {key}")
        path = self.root / key[:2] / key
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(hashlib.sha256(content).hexdigest().encode() + b"\n" + content)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
