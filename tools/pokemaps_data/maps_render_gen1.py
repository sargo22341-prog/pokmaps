"""Couleurs des cartes et des sprites de la 1re génération : palettes du Super Game Boy.

Chaque ville a sa palette, les routes partagent la même, les bâtiments prennent celle de la ville ou de la route
où ils se trouvent (SetPal_Overworld dans engine/gfx/palettes.asm).
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from PIL import Image

from .maps_layout import GameMaps, identifier
from .maps_render import MapRenderer, paint_tile, sprite_image, tile_shades
from .pret import BLOCK_PX, PretMap, PretRepo
from .webp import WEBP_LOSSLESS

# Palettes particulières (cf. SetPal_Overworld dans engine/gfx/palettes.asm).
CEMETERY_TILESET, CAVERN_TILESET = "CEMETERY", "CAVERN"
CAVE_MAPS = frozenset({"CERULEAN_CAVE_2F", "CERULEAN_CAVE_B1F", "CERULEAN_CAVE_1F", "BRUNOS_ROOM"})
LORELEI_MAP = "LORELEIS_ROOM"
# Palette des sprites de personnages, la même partout dans le jeu.
SPRITE_PALETTE = "PAL_ROUTE"


class Gen1Renderer(MapRenderer):
    """Dessine les cartes de Rouge, Bleu et Jaune avec les tilesets et palettes de leur désassemblage."""

    def __init__(self, game_maps: GameMaps, repo: PretRepo) -> None:
        super().__init__(game_maps)
        self.repo = repo
        # Métatuiles déjà colorées, par (tileset, palette), partagées entre les cartes du jeu.
        self._cache: dict[tuple[str, str], list[Image.Image]] = {}

    def palette_name(self, const: str) -> str:
        pret_map = self.maps[const]
        if pret_map.tileset == CEMETERY_TILESET:
            return "PAL_GRAYMON"
        if pret_map.tileset == CAVERN_TILESET or const in CAVE_MAPS:
            return "PAL_CAVE"
        if const == LORELEI_MAP:
            return "PAL_PALLET"
        if not pret_map.is_outdoor:
            pret_map = self.maps[self.game_maps.parents[const]]
        if pret_map.number < self.maps["ROUTE_1"].number:
            return self.repo.palette_order[pret_map.number + 1]
        return "PAL_ROUTE"

    @cached_property
    def _tileset_images(self) -> dict[str, Image.Image]:
        """Tilesets en indices de couleur (0 = clair … 3 = foncé)."""
        return {const: tile_shades(tileset.gfx) for const, tileset in self.repo.tilesets.items()}

    def blocks(self, pret_map: PretMap) -> list[Image.Image]:
        key = (pret_map.tileset, self.palette_name(pret_map.const))
        if key not in self._cache:
            self._cache[key] = self._colored_blocks(*key)
        return self._cache[key]

    def _colored_blocks(self, tileset: str, palette: str) -> list[Image.Image]:
        tiles = self._tileset_images[tileset]
        data = self.repo.tilesets[tileset].blockset.read_bytes()
        colors = [channel for color in self.repo.palettes[palette] for channel in color]
        blocks = []
        for index in range(len(data) // 16):
            block = Image.new("P", (BLOCK_PX, BLOCK_PX))
            for position, tile in enumerate(data[index * 16 : index * 16 + 16]):
                # Une tuile hors du tileset n'est jamais affichée par le jeu : elle reste de la couleur 0.
                paint_tile(block, tiles, tile, position)
            block.putpalette(colors)
            blocks.append(block.convert("RGB"))
        return blocks

    def write_sprites(self, sprites: set[str], output: Path) -> None:
        colors = self.repo.palettes[SPRITE_PALETTE]
        for sprite in sorted(sprites):
            path = self.repo.sprites.get(sprite)
            if path is None:
                continue
            output.mkdir(parents=True, exist_ok=True)
            name = identifier(sprite.removeprefix("SPRITE_"))
            sprite_image(path, colors).save(output / f"{name}.webp", "WEBP", **WEBP_LOSSLESS)
