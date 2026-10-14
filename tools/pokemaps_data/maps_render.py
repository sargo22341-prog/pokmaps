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
from .pret import TILE_PX, PretMap

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

    def write_display(self, const: str, output: Path) -> DisplayMap:
        """Rend une carte affichée et écrit ses tuiles dans `output`."""
        display = self.render(const)
        write_tiles(display, output)
        return display

    def render(self, const: str) -> DisplayMap:
        if const in self.game_maps.world_blocks:
            return self._render_world(const)
        if const in self.game_maps.plans:
            return self._render_plan(const)
        pret_map = self.maps[const]
        width, height = pret_map.width * self.game_maps.block_px, pret_map.height * self.game_maps.block_px
        canvas = Image.new("RGB", (width, height))
        self._paint(canvas, pret_map, (0, 0))
        return DisplayMap(const, width, height, level_count(width, height), canvas)

    def _render_plan(self, const: str) -> DisplayMap:
        plan = self.game_maps.plans[const]
        canvas = Image.new("RGBA", (plan.width, plan.height))
        for part in plan.parts:
            self._paint(canvas, self.maps[part.map], (part.x, part.y))
        return DisplayMap(const, plan.width, plan.height, level_count(plan.width, plan.height), canvas)

    def _paint(self, canvas: Image.Image, pret_map: PretMap, origin: tuple[int, int]) -> None:
        blocks = self.blocks(pret_map)
        for y in range(pret_map.height):
            for x in range(pret_map.width):
                position = (origin[0] + x * self.game_maps.block_px, origin[1] + y * self.game_maps.block_px)
                canvas.paste(blocks[pret_map.block(x, y)], position)

    def _render_world(self, region: str) -> DisplayMap:
        world = self.game_maps.world_blocks[region]
        columns, rows = self.game_maps.world_size(region)
        size = self.game_maps.block_px
        canvas = Image.new("RGBA", (columns * size, rows * size))
        owner: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        for const, (bx, by) in world.items():
            pret_map = self.maps[const]
            self._paint(canvas, pret_map, (bx * size, by * size))
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
        borders: dict[tuple[int, int], tuple[int, str]] = {}
        rows, columns = len(owner), len(owner[0])
        for const, (left, top) in world.items():
            current = self.maps[const]
            right, bottom = left + current.width - 1, top + current.height - 1
            for y in range(max(0, top - BORDER_MARGIN), min(rows, bottom + BORDER_MARGIN + 1)):
                for x in range(max(0, left - BORDER_MARGIN), min(columns, right + BORDER_MARGIN + 1)):
                    if owner[y][x] is not None:
                        continue
                    distance = max(left - x, 0, x - right, top - y, y - bottom)
                    previous = borders.get((x, y))
                    if previous is None or distance < previous[0]:
                        borders[x, y] = (distance, const)
        size = self.game_maps.block_px
        for (x, y), (_, const) in borders.items():
            left, top = world[const]
            canvas.paste(self.border(self.maps[const], x - left, y - top), (x * size, y * size))

    def border(self, pret_map: PretMap, x: int, y: int) -> Image.Image:
        return self.blocks(pret_map)[pret_map.border_block]


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


def write_region_tiles(image: Image.Image, origin: tuple[int, int], size: tuple[int, int], output: Path) -> int:
    """Tuiles d'une image placée en `origin` dans une carte de taille `size`, sur la grille de cette carte.

    Seules les tuiles que l'image touche sont écrites, à chaque niveau de zoom ; la réduction de chaque niveau
    part d'un cadre aligné sur son facteur, comme la carte entière, pour que les pixels coïncident."""
    levels = level_count(*size)
    count = 0
    for level in range(levels):
        factor = 2 ** (levels - 1 - level)
        left, top = (origin[0] // factor) * factor, (origin[1] // factor) * factor
        right = math.ceil((origin[0] + image.width) / factor) * factor
        bottom = math.ceil((origin[1] + image.height) / factor) * factor
        frame = Image.new("RGBA", (right - left, bottom - top))
        frame.paste(image, (origin[0] - left, origin[1] - top))
        if factor > 1:
            frame = frame.resize((frame.width // factor, frame.height // factor), Image.Resampling.BOX)
        x0, y0 = left // factor, top // factor
        for row in range(y0 // TILE_SIZE, math.ceil((y0 + frame.height) / TILE_SIZE)):
            for column in range(x0 // TILE_SIZE, math.ceil((x0 + frame.width) / TILE_SIZE)):
                tile = Image.new("RGBA", (TILE_SIZE, TILE_SIZE))
                tile.paste(frame, (x0 - column * TILE_SIZE, y0 - row * TILE_SIZE))
                if tile.getextrema()[3][1] == 0:
                    continue
                path = output / str(level) / f"{row}_{column}.webp"
                path.parent.mkdir(parents=True, exist_ok=True)
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
