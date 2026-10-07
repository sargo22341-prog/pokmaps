"""Images des lieux, recomposées depuis les tuiles WebP générées dans les assets."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PIL import Image

from .catalog import EditorMap

_TILE_SIZE = 256
_BACKGROUND = (238, 238, 238, 255)
# Quelques lieux récents suffisent pour passer de l'un à l'autre sans relire les tuiles.
_CACHE_SIZE = 6


class MapImages:
    """Recompose, à sa taille native, la partie de la carte affichée qui couvre un lieu."""

    def __init__(self, maps_root: Path) -> None:
        self.maps_root = maps_root
        self._cache: OrderedDict[tuple[str, str], Image.Image] = OrderedDict()

    def image(self, editor_map: EditorMap) -> Image.Image:
        key = (editor_map.version_group, editor_map.identifier)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        image = self._compose(editor_map)
        self._cache[key] = image
        if len(self._cache) > _CACHE_SIZE:
            self._cache.popitem(last=False)
        return image

    def _compose(self, editor_map: EditorMap) -> Image.Image:
        folder = self.maps_root / editor_map.version_group / editor_map.displayed
        levels = [int(path.name) for path in folder.iterdir() if path.is_dir() and path.name.isdigit()]
        if not levels:
            raise FileNotFoundError(f"Tuiles absentes pour {editor_map.displayed} : {folder}")
        source = folder / str(max(levels))
        left, top = editor_map.x, editor_map.y
        image = Image.new("RGBA", (editor_map.width, editor_map.height), _BACKGROUND)
        for row in range(top // _TILE_SIZE, (top + editor_map.height - 1) // _TILE_SIZE + 1):
            for column in range(left // _TILE_SIZE, (left + editor_map.width - 1) // _TILE_SIZE + 1):
                path = source / f"{row}_{column}.webp"
                # Les tuiles entièrement vides ne sont pas écrites par la génération.
                if not path.is_file():
                    continue
                with Image.open(path) as tile:
                    tile_image = tile.convert("RGBA")
                position = (column * _TILE_SIZE - left, row * _TILE_SIZE - top)
                image.paste(tile_image, position, tile_image.getchannel("A"))
        return image
