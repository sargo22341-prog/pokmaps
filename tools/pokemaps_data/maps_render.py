"""Rendu des cartes en images pixel-art et découpage en tuiles pour MapCompose.

Les couleurs sont celles du Super Game Boy : chaque ville a sa palette, les routes partagent la même, les
bâtiments prennent celle de la ville ou de la route où ils se trouvent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from PIL import Image

from .maps_layout import WORLD, GameMaps, identifier
from .pret import BLOCK_PX, TILE_PX, PretMap, PretRepo

TILE_SIZE = 256
# Blocs de bordure dessinés autour des villes et routes (le jeu en affiche 4 à 5 au bord de l'écran).
BORDER_MARGIN = 4

# Palettes particulières (cf. SetPal_Overworld dans engine/gfx/palettes.asm).
CEMETERY_TILESET, CAVERN_TILESET = "CEMETERY", "CAVERN"
CAVE_MAPS = frozenset({"CERULEAN_CAVE_2F", "CERULEAN_CAVE_B1F", "CERULEAN_CAVE_1F", "BRUNOS_ROOM"})
LORELEI_MAP = "LORELEIS_ROOM"

# Blocs déjà colorés, par (tileset, palette), partagés entre les cartes d'un même jeu.
BlockCache = dict[tuple[str, str], list[Image.Image]]


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


class MapRenderer:
    """Dessine les cartes d'un jeu avec les tilesets et palettes de son désassemblage."""

    def __init__(self, game_maps: GameMaps) -> None:
        self.game_maps = game_maps
        self.repo = game_maps.repo
        self.maps = game_maps.maps
        self._cache: BlockCache = {}

    def palette_name(self, const: str) -> str:
        pret_map = self.maps[const]
        if pret_map.tileset == CEMETERY_TILESET:
            return "PAL_GRAYMON"
        if pret_map.tileset == CAVERN_TILESET or const in CAVE_MAPS:
            return "PAL_CAVE"
        if const == LORELEI_MAP:
            return "PAL_PALLET"
        if not pret_map.is_outdoor:
            pret_map = self.maps[self.game_maps.indoor_parents[const]]
        if pret_map.number < self.maps["ROUTE_1"].number:
            return self.repo.palette_order[pret_map.number + 1]
        return "PAL_ROUTE"

    # --- Rendu ----------------------------------------------------------------

    @cached_property
    def _tileset_images(self) -> dict[str, Image.Image]:
        """Tilesets en indices de couleur (0 = clair … 3 = foncé)."""
        result = {}
        for const, tileset in self.repo.tilesets.items():
            gray = Image.open(tileset.gfx).convert("L")
            result[const] = gray.point(lambda v: 3 - round(v / 85))
        return result

    def _blocks(self, tileset: str, palette: str) -> list[Image.Image]:
        key = (tileset, palette)
        cache = self._cache
        if key not in cache:
            tiles = self._tileset_images[tileset]
            columns = tiles.width // TILE_PX
            data = self.repo.tilesets[tileset].blockset.read_bytes()
            colors = [channel for color in self.repo.palettes[palette] for channel in color]
            blocks = []
            for index in range(len(data) // 16):
                block = Image.new("P", (BLOCK_PX, BLOCK_PX))
                for position, tile in enumerate(data[index * 16 : index * 16 + 16]):
                    if tile >= columns * (tiles.height // TILE_PX):
                        continue  # tuile hors du tileset (jamais affichée par le jeu)
                    source = ((tile % columns) * TILE_PX, (tile // columns) * TILE_PX)
                    crop = tiles.crop((*source, source[0] + TILE_PX, source[1] + TILE_PX))
                    block.paste(crop, ((position % 4) * TILE_PX, (position // 4) * TILE_PX))
                block.putpalette(colors)
                blocks.append(block.convert("RGB"))
            cache[key] = blocks
        return cache[key]

    def _paint(self, canvas: Image.Image, pret_map: PretMap, origin: tuple[int, int]) -> None:
        blocks = self._blocks(pret_map.tileset, self.palette_name(pret_map.const))
        for y in range(pret_map.height):
            for x in range(pret_map.width):
                position = (origin[0] + x * BLOCK_PX, origin[1] + y * BLOCK_PX)
                canvas.paste(blocks[pret_map.block(x, y)], position)

    def render(self, const: str) -> DisplayMap:
        if const == WORLD:
            return self._render_world()
        pret_map = self.maps[const]
        width, height = pret_map.width * BLOCK_PX, pret_map.height * BLOCK_PX
        canvas = Image.new("RGB", (width, height))
        self._paint(canvas, pret_map, (0, 0))
        return DisplayMap(const, width, height, level_count(width, height), canvas)

    def _render_world(self) -> DisplayMap:
        columns, rows = self.game_maps.world_size
        canvas = Image.new("RGBA", (columns * BLOCK_PX, rows * BLOCK_PX))
        owner: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        for const, (bx, by) in self.game_maps.world_blocks.items():
            pret_map = self.maps[const]
            self._paint(canvas, pret_map, (bx * BLOCK_PX, by * BLOCK_PX))
            for y in range(pret_map.height):
                for x in range(pret_map.width):
                    owner[by + y][bx + x] = const
        # Autour des cartes : le bloc de bordure de la carte la plus proche, sur la largeur visible à l'écran
        # dans le jeu. Au-delà, la carte du monde reste transparente.
        rects = [(*self.game_maps.world_blocks[const], self.maps[const]) for const in self.game_maps.world_blocks]

        def distance(rect: tuple[int, int, PretMap], x: int, y: int) -> int:
            left, top, pret_map = rect
            dx = max(left - x, 0, x - (left + pret_map.width - 1))
            dy = max(top - y, 0, y - (top + pret_map.height - 1))
            return max(dx, dy)

        for y in range(rows):
            for x in range(columns):
                if owner[y][x] is not None:
                    continue
                nearest = min(rects, key=lambda rect: distance(rect, x, y))
                if distance(nearest, x, y) > BORDER_MARGIN:
                    continue
                pret_map = nearest[2]
                blocks = self._blocks(pret_map.tileset, self.palette_name(pret_map.const))
                canvas.paste(blocks[pret_map.border_block], (x * BLOCK_PX, y * BLOCK_PX))
        width, height = canvas.size
        return DisplayMap(WORLD, width, height, level_count(width, height), canvas)


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
                tile.save(path, "WEBP", lossless=True, method=4)
                count += 1
    return count


def write_sprites(repo: PretRepo, sprites: set[str], output: Path) -> None:
    """Première image (de face) des sprites de PNJ utilisés, couleur 0 transparente."""
    colors = repo.palettes["PAL_ROUTE"]
    for sprite in sorted(sprites):
        path = repo.sprites.get(sprite)
        if path is None:
            continue
        gray = Image.open(path).convert("L").crop((0, 0, 16, 16))
        image = Image.new("RGBA", gray.size)
        for y in range(gray.height):
            for x in range(gray.width):
                shade = 3 - round(gray.getpixel((x, y)) / 85)
                image.putpixel((x, y), (*colors[shade], 0 if shade == 0 else 255))
        output.mkdir(parents=True, exist_ok=True)
        image.save(output / f"{identifier(sprite.removeprefix('SPRITE_'))}.png", optimize=True)
