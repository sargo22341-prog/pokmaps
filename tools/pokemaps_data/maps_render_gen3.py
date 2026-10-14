"""Rendu GBA : tuiles 4 bpp, retournements, palettes et deux couches de métatuiles."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from PIL import Image

from .maps_layout_gen3 import MIRAGE_ISLAND, MIRAGE_ROUTE, Gen3GameMaps
from .maps_render import DisplayMap, MapRenderer, level_count, write_region_tiles
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Map
from .pret_gen3_tilesets import Gen3Metatile, Gen3Tileset, map_palettes


def tile_pixels(tileset: Gen3Tileset, number: int) -> bytes:
    if not 0 <= number < tileset.tile_count:
        raise ValueError(f"{tileset.const} : tuile absente : {number}")
    columns = tileset.image_width // 8
    left, top = (number % columns) * 8, (number // columns) * 8
    return bytes(tileset.pixels[(top + y) * tileset.image_width + left + x] for y in range(8) for x in range(8))


def paint_metatile(
    metatile: Gen3Metatile,
    pixels: dict[int, bytes],
    palettes: tuple[tuple[tuple[int, int, int], ...], ...],
) -> Image.Image:
    if metatile.layer_type not in {0, 1, 2}:
        raise ValueError(f"Couche GBA inconnue : {metatile.layer_type}")
    image = Image.new("RGB", (16, 16), palettes[0][0])
    # Le moteur place 0x3014 derrière les deux couches du type NORMAL.
    descriptors = ((0x3014,) * 4 if metatile.layer_type == 0 else ()) + metatile.tiles
    for position, descriptor in enumerate(descriptors):
        number, palette = descriptor & 0x3FF, descriptor >> 12
        if number not in pixels or palette >= len(palettes):
            raise ValueError(f"Descripteur GBA invalide : {descriptor:#06x}")
        shades = pixels[number]
        for y in range(8):
            for x in range(8):
                sx = 7 - x if descriptor & 0x400 else x
                sy = 7 - y if descriptor & 0x800 else y
                shade = shades[sy * 8 + sx]
                if shade:
                    index = position % 4
                    image.putpixel(((index % 2) * 8 + x, (index // 2) * 8 + y), palettes[palette][shade])
    return image


class Gen3Renderer(MapRenderer):
    def __init__(self, game_maps: Gen3GameMaps, repo: Gen3PretRepo) -> None:
        super().__init__(game_maps)
        self.repo = repo
        self._blocks: dict[tuple[str, str], list[Image.Image]] = {}
        self._validated: set[str] = set()

    def blocks(self, pret_map: Gen3Map) -> list[Image.Image]:
        layout = pret_map.layout
        key = (layout.primary_tileset, layout.secondary_tileset)
        if key not in self._blocks:
            self._blocks[key] = self._render_blocks(*key)
        result = self._blocks[key]
        if pret_map.const in self._validated:
            return result
        for cell in (*layout.cells, *layout.border):
            number = cell & 0x3FF
            primary = self.repo.tilesets[layout.primary_tileset]
            secondary = self.repo.tilesets[layout.secondary_tileset]
            valid = number < len(primary.metatiles) or (
                primary.primary_metatile_count <= number < primary.primary_metatile_count + len(secondary.metatiles)
            )
            if not valid:
                raise ValueError(f"{pret_map.const} : métatuile absente : {number}")
        self._validated.add(pret_map.const)
        return result

    def _render_blocks(self, primary_name: str, secondary_name: str) -> list[Image.Image]:
        from .pret_gen3_animation import animation_tiles

        primary, secondary = self.repo.tilesets[primary_name], self.repo.tilesets[secondary_name]
        # Les palettes réservées sont présentes dans les sources (notamment les fenêtres de Bourg-en-Vol).
        palettes = map_palettes(primary, secondary) + secondary.palettes[13:]
        # La VRAM non chargée reste transparente ; certains métatiles la référencent derrière une couche opaque.
        pixels = dict.fromkeys(range(1024), bytes(64))
        pixels |= {number: tile_pixels(primary, number) for number in range(primary.tile_count)}
        pixels |= {
            primary.primary_tile_count + number: tile_pixels(secondary, number)
            for number in range(secondary.tile_count)
        }
        pixels |= animation_tiles(self.repo, primary) | animation_tiles(self.repo, secondary)
        used = {
            cell & 0x3FF
            for current in self.maps.values()
            if (current.layout.primary_tileset, current.layout.secondary_tileset) == (primary_name, secondary_name)
            for cell in (*current.layout.cells, *current.layout.border)
        }
        images = [Image.new("RGB", (16, 16)) for _ in range(1024)]
        for number in used:
            offset = primary.primary_metatile_count
            source = primary if number < offset else secondary
            index = number if number < offset else number - offset
            if index >= len(source.metatiles):
                raise ValueError(f"{source.const} : métatuile absente : {index}")
            images[number] = paint_metatile(source.metatiles[index], pixels, palettes)
        return images

    def write_display(self, const: str, output: Path) -> DisplayMap:
        if const != MIRAGE_ISLAND:
            return super().write_display(const, output)
        # L'île est dessinée sur la grille de la carte du monde, seulement là où elle change la route.
        island = self.maps[const]
        blocks = self.blocks(island)
        image = Image.new("RGBA", (island.width * 16, island.height * 16))
        for x, y in self.game_maps.mirage_cells:
            image.paste(blocks[island.block(x, y)], (x * 16, y * 16))
        columns, rows = self.game_maps.world_size(self.game_maps.world_region[MIRAGE_ROUTE])
        size = (columns * 16, rows * 16)
        write_region_tiles(image, self.game_maps.detached_origin(const), size, output)
        return DisplayMap(const, *size, level_count(*size), image)

    def write_sea(self, region: str, output: Path) -> int:
        """Eau de bordure répétée, une tuile par niveau de zoom de la carte du monde `region` : l'application la
        dessine sous la carte pour prolonger la mer sans délimitation. Chaque niveau réduit la métatuile comme
        la carte entière (moyenne par carré du facteur de zoom). Renvoie le nombre de niveaux."""
        blocks = self.game_maps.world_blocks[region]
        borders = Counter(cell & 0x3FF for const in blocks for cell in self.maps[const].layout.border)
        number, _ = borders.most_common(1)[0]
        sample = self.maps[next(const for const in blocks if number in self.maps[const].layout.border)]
        primary = self.repo.tilesets[sample.layout.primary_tileset]
        if number >= primary.primary_metatile_count:
            raise ValueError(f"{region} : eau de bordure hors du tileset commun : {number}")
        if primary.metatiles[number].behavior not in self.repo.terrain_rules.surfable:
            raise ValueError(f"{region} : la bordure la plus fréquente n'est pas de l'eau : {number}")
        water = self.blocks(sample)[number]
        columns, rows = self.game_maps.world_size(region)
        levels = level_count(columns * 16, rows * 16)
        output.mkdir(parents=True, exist_ok=True)
        for level in range(levels):
            side = max(1, 16 // 2 ** (levels - 1 - level))
            pattern = water.resize((side, side), Image.Resampling.BOX)
            tile = Image.new("RGB", (256, 256))
            for y in range(0, 256, side):
                for x in range(0, 256, side):
                    tile.paste(pattern, (x, y))
            tile.save(output / f"{level}.webp", "WEBP", lossless=True, method=4)
        return levels

    def border(self, pret_map: Gen3Map, x: int, y: int) -> Image.Image:
        layout = pret_map.layout
        index = (y % layout.border_height) * layout.border_width + x % layout.border_width
        return self.blocks(pret_map)[layout.border[index] & 0x3FF]

    def write_sprites(self, sprites: set[str], output: Path) -> None:
        from .pret_gen3_sprites import write_sprites

        write_sprites(self.repo, sprites, output)
