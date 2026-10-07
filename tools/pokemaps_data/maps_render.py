"""Rendu des cartes en images pixel-art et découpage en tuiles pour MapCompose.

Ce module assemble les cartes affichées (cartes du monde et cartes à part) et les découpe en tuiles ; les
couleurs de chaque métatuile et des sprites viennent du rendu du format du jeu (`maps_render_gen1.py` : palettes
du Super Game Boy ; `maps_render_gen2.py` : palettes de la Game Boy Color).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from .maps_layout import GameMaps
from .pret import BLOCK_PX, TILE_PX, PretMap

TILE_SIZE = 256
# Métatuiles de bordure dessinées autour des villes et routes (le jeu en affiche 4 à 5 au bord de l'écran).
BORDER_MARGIN = 4
# Taille d'une image de sprite : la première image du fichier, de face.
SPRITE_PX = 16


@dataclass
class DisplayMap:
    const: str
    width: int  # en pixels
    height: int
    level_count: int
    image: Image.Image = field(repr=False)


def level_count(width: int, height: int) -> int:
    """Nombre de niveaux de zoom : le plus petit tient dans une tuile."""
    return 1 + max(0, math.ceil(math.log2(max(width, height) / TILE_SIZE)))


def tile_shades(path: Path) -> Image.Image:
    """Image en niveaux de gris 2 bits d'un fichier pret, en indices de couleur (0 = clair … 3 = foncé)."""
    gray = Image.open(path).convert("L")
    return gray.point(lambda v: 3 - round(v / 85))


def paint_tile(block: Image.Image, tiles: Image.Image, tile: int, position: int) -> bool:
    """Colle la tuile `tile` de l'image `tiles` à la place `position` (0 à 15) d'une métatuile de 4 × 4 tuiles.

    Renvoie False si la tuile n'est pas dans l'image."""
    columns = tiles.width // TILE_PX
    if tile >= columns * (tiles.height // TILE_PX):
        return False
    source = ((tile % columns) * TILE_PX, (tile // columns) * TILE_PX)
    crop = tiles.crop((*source, source[0] + TILE_PX, source[1] + TILE_PX))
    block.paste(crop, ((position % 4) * TILE_PX, (position // 4) * TILE_PX))
    return True


class MapRenderer(ABC):
    """Dessine les cartes d'un jeu ; chaque format fournit les images de ses métatuiles et de ses sprites."""

    def __init__(self, game_maps: GameMaps) -> None:
        self.game_maps = game_maps
        self.maps = game_maps.maps

    @abstractmethod
    def blocks(self, pret_map: PretMap) -> list[Image.Image]:
        """Images RVB (32 × 32 px) des métatuiles du tileset de la carte, dans les couleurs de la carte."""

    @abstractmethod
    def write_sprites(self, sprites: set[str], output: Path) -> None:
        """Première image (de face) des sprites de personnages utilisés, fond transparent."""

    def render(self, const: str) -> DisplayMap:
        if const in self.game_maps.world_blocks:
            return self._render_world(const)
        pret_map = self.maps[const]
        width, height = pret_map.width * BLOCK_PX, pret_map.height * BLOCK_PX
        canvas = Image.new("RGB", (width, height))
        self._paint(canvas, pret_map, (0, 0))
        return DisplayMap(const, width, height, level_count(width, height), canvas)

    def _paint(self, canvas: Image.Image, pret_map: PretMap, origin: tuple[int, int]) -> None:
        blocks = self.blocks(pret_map)
        for y in range(pret_map.height):
            for x in range(pret_map.width):
                position = (origin[0] + x * BLOCK_PX, origin[1] + y * BLOCK_PX)
                canvas.paste(blocks[pret_map.block(x, y)], position)

    def _render_world(self, region: str) -> DisplayMap:
        world = self.game_maps.world_blocks[region]
        columns, rows = self.game_maps.world_size(region)
        canvas = Image.new("RGBA", (columns * BLOCK_PX, rows * BLOCK_PX))
        owner: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        for const, (bx, by) in world.items():
            pret_map = self.maps[const]
            self._paint(canvas, pret_map, (bx * BLOCK_PX, by * BLOCK_PX))
            for y in range(pret_map.height):
                for x in range(pret_map.width):
                    owner[by + y][bx + x] = const
        self._paint_borders(canvas, world, owner)
        width, height = canvas.size
        return DisplayMap(region, width, height, level_count(width, height), canvas)

    def _paint_borders(
        self, canvas: Image.Image, world: dict[str, tuple[int, int]], owner: list[list[str | None]]
    ) -> None:
        """Autour des cartes : la métatuile de bordure de la carte la plus proche, sur la largeur visible à l'écran
        dans le jeu. Au-delà, la carte du monde reste transparente."""
        rects = [(*world[const], self.maps[const]) for const in world]

        def distance(rect: tuple[int, int, PretMap], x: int, y: int) -> int:
            left, top, pret_map = rect
            dx = max(left - x, 0, x - (left + pret_map.width - 1))
            dy = max(top - y, 0, y - (top + pret_map.height - 1))
            return max(dx, dy)

        for y, row in enumerate(owner):
            for x, const in enumerate(row):
                if const is not None:
                    continue
                nearest = min(rects, key=lambda rect: distance(rect, x, y))
                if distance(nearest, x, y) > BORDER_MARGIN:
                    continue
                pret_map = nearest[2]
                canvas.paste(self.blocks(pret_map)[pret_map.border_block], (x * BLOCK_PX, y * BLOCK_PX))


def write_tiles(display: DisplayMap, output: Path) -> int:
    """Découpe la carte en tuiles WebP sans perte, pour chaque niveau de zoom. Renvoie le nombre de tuiles.

    Les tuiles entièrement transparentes ne sont pas écrites."""
    count = 0
    full = display.image.convert("RGBA")
    for level in range(display.level_count):
        factor = 2 ** (display.level_count - 1 - level)
        size = (math.ceil(display.width / factor), math.ceil(display.height / factor))
        image = full if factor == 1 else full.resize(size, Image.Resampling.BOX)
        for row in range(math.ceil(size[1] / TILE_SIZE)):
            for column in range(math.ceil(size[0] / TILE_SIZE)):
                box = (column * TILE_SIZE, row * TILE_SIZE, (column + 1) * TILE_SIZE, (row + 1) * TILE_SIZE)
                # Les tuiles du bord sont complétées par de la transparence pour garder 256 × 256 px.
                tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
                tile.paste(image.crop((box[0], box[1], min(box[2], size[0]), min(box[3], size[1]))))
                if tile.getextrema()[3][1] == 0:
                    continue  # tuile entièrement transparente : l'application n'affiche rien
                path = output / str(level) / f"{row}_{column}.webp"
                path.parent.mkdir(parents=True, exist_ok=True)
                # method=4 et non 6 : 6 n'allège les tuiles que de 4 % (mesuré), pour un encodage 25 fois plus long.
                tile.save(path, "WEBP", lossless=True, method=4)
                count += 1
    return count


def sprite_image(path: Path, colors: tuple[tuple[int, int, int], ...]) -> Image.Image:
    """Première image (de face) d'un sprite, dans les 4 couleurs `colors` ; la couleur 0 est transparente."""
    shades = tile_shades(path).crop((0, 0, SPRITE_PX, SPRITE_PX))
    image = Image.new("RGBA", shades.size)
    for y in range(shades.height):
        for x in range(shades.width):
            shade = shades.getpixel((x, y))
            image.putpixel((x, y), (*colors[shade], 0 if shade == 0 else 255))
    return image
