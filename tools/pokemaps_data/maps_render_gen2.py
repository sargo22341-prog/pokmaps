"""Couleurs des cartes et des sprites de la 2e génération : palettes de la Game Boy Color, de jour.

Chaque tuile d'un tileset a sa palette (GRAY, RED… : gfx/tilesets/*_palette_map.asm). Les 8 palettes chargées
dépendent de l'environnement de la carte et du moment de la journée (LoadMapPals, engine/gfx/color.asm) :
data/maps/environment_colors.asm choisit, pour chaque environnement et chaque moment, 8 palettes de
gfx/tilesets/bg_tiles.pal. En ville et sur les routes, les toits prennent les couleurs du groupe de la carte
(gfx/tilesets/roofs.pal) et, pour les tilesets de Johto, ses tuiles (gfx/tilesets/roofs/*.png).

Le moment rendu est le jour : celui que la carte affiche en journée d'après sa palette (ReplaceTimeOfDayPals,
engine/tilesets/timeofday_pals.asm). Une grotte sombre (PALETTE_DARK) est rendue comme après Flash.
"""

from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

from PIL import Image

from .maps_layout import GameMaps, identifier
from .maps_render import MapRenderer, paint_tile, sprite_image, tile_shades
from .pret import BLOCK_PX, PretMap
from .pret_gen2 import OUTDOOR_ENVIRONMENTS, Gen2PretRepo, MapHeader
from .pret_source import macro_args, parse_int, source_lines
from .webp import WEBP_LOSSLESS

Color = tuple[int, int, int]
Palette = tuple[Color, ...]

# Moments de la journée (shift_const de constants/ram_constants.asm) : rang des lignes de environment_colors.asm.
TIMES = ("MORN", "DAY", "NITE", "DARKNESS")
RENDERED_TIME = "DAY"
# Après Flash, une grotte sombre prend les couleurs de la nuit (ReplaceTimeOfDayPals.UsedFlash).
DARK_PALETTE, FLASH_TIME = "PALETTE_DARK", "NITE"
# Palettes de tuile, dans l'ordre des palettes chargées (PAL_BG_*, constants/tileset_constants.asm).
TILE_PALETTES = ("GRAY", "RED", "GREEN", "WATER", "YELLOW", "BROWN", "ROOF", "TEXT")
ROOF_PALETTE = TILE_PALETTES.index("ROOF")
# Tilesets dont les tuiles de toit dépendent du groupe de la carte, et place de ces tuiles (LoadTilesetGFX,
# LoadMapGroupRoof : ROOF_LENGTH tuiles à partir de la tuile $0a).
ROOF_TILESETS = frozenset({"TILESET_JOHTO", "TILESET_JOHTO_MODERN"})
ROOF_FIRST_TILE, ROOF_LENGTH = 0x0A, 9
# Tuile « espace » de la police, chargée à la fin de la VRAM des tuiles (LoadFrame) : entièrement de la couleur 0.
SPACE_TILE = 0x7F
_RGB = re.compile(r"^RGB ([\d, ]+)$")


def _rgb(line: str) -> list[Color]:
    """Couleurs d'une ligne « RGB r, g, b[, r, g, b…] » (composantes sur 5 bits) en RVB 8 bits."""
    match = _RGB.match(line)
    if match is None:
        raise ValueError(f"Couleur illisible : {line}")
    values = [int(value) for value in match.group(1).replace(",", " ").split()]
    if len(values) % 3:
        raise ValueError(f"Couleur incomplète : {line}")
    return [_color(*values[i : i + 3]) for i in range(0, len(values), 3)]


def _color(red: int, green: int, blue: int) -> Color:
    """Composantes de 5 bits étendues sur 8 bits, comme l'écran de la Game Boy Color les restitue au mieux."""
    return (red << 3) | (red >> 2), (green << 3) | (green >> 2), (blue << 3) | (blue >> 2)


class Gen2Renderer(MapRenderer):
    """Dessine les cartes d'Or et d'Argent avec les tilesets et les palettes Game Boy Color de leur désassemblage."""

    def __init__(self, game_maps: GameMaps, repo: Gen2PretRepo) -> None:
        super().__init__(game_maps)
        self.repo = repo
        self._cache: dict[tuple[str, tuple[Palette, ...], int | None], tuple[list[Image.Image], frozenset[int]]] = {}

    # --- Palettes -------------------------------------------------------------

    @cached_property
    def _bg_palettes(self) -> list[Palette]:
        """Palettes de gfx/tilesets/bg_tiles.pal, dans l'ordre (index utilisé par environment_colors.asm)."""
        lines = source_lines(self.repo.path("gfx/tilesets/bg_tiles.pal"))
        return [tuple(_rgb(line)) for line in lines if line.startswith("RGB ")]

    @cached_property
    def _environment_colors(self) -> dict[str, list[list[int]]]:
        """Environnement (TOWN…) -> pour chaque moment de la journée, 8 index de bg_tiles.pal."""
        lines = source_lines(self.repo.path("data/maps/environment_colors.asm"))
        labels = [macro_args(line, "dw")[0] for line in lines if line.startswith("dw ")]
        tables: dict[str, list[list[int]]] = {}
        current = None
        for line in lines:
            if line.endswith(":") and line.startswith("."):
                current = tables.setdefault(line[:-1], [])
            elif current is not None and line.startswith("db "):
                current.append([parse_int(value) for value in macro_args(line, "db")])
        environments = self.repo.consts("constants/map_data_constants.asm", until="NUM_ENVIRONMENTS")
        # La table commence par une entrée inutilisée : les environnements valent 1 à NUM_ENVIRONMENTS.
        return {environment: tables[labels[index + 1]] for index, environment in enumerate(environments)}

    @cached_property
    def _day_times(self) -> dict[str, str]:
        """Palette de carte (PALETTE_AUTO…) -> moment dont elle prend les couleurs en journée (BrightnessLevels)."""
        palettes = [
            line.split()[1]
            for line in source_lines(self.repo.path("constants/map_data_constants.asm"))
            if line.startswith("const PALETTE_")
        ]
        lines = source_lines(self.repo.path("engine/tilesets/timeofday_pals.asm"))
        start = lines.index(".BrightnessLevels:") + 1
        rows = [macro_args(line, "dc") for line in lines[start : start + len(palettes)]]
        # Colonnes de dc : moment réel DARKNESS, NITE, DAY, MORN ; on garde la colonne DAY.
        result = {palette: row[2].removesuffix("_F") for palette, row in zip(palettes, rows, strict=True)}
        result[DARK_PALETTE] = FLASH_TIME
        return result

    @cached_property
    def _roof_colors(self) -> list[tuple[Color, Color]]:
        """Groupe de cartes -> 2 couleurs de toit de jour (gfx/tilesets/roofs.pal : 2 de jour, 2 de nuit)."""
        colors = [color for line in source_lines(self.repo.path("gfx/tilesets/roofs.pal")) for color in _rgb(line)]
        return [(colors[index], colors[index + 1]) for index in range(0, len(colors), 4)]

    def palettes(self, header: MapHeader) -> tuple[Palette, ...]:
        """Les 8 palettes chargées pour la carte, de jour."""
        time = TIMES.index(self._day_times[header.palette])
        indexes = self._environment_colors[header.environment][time]
        palettes = [self._bg_palettes[index] for index in indexes]
        if header.environment in OUTDOOR_ENVIRONMENTS:
            roof = palettes[ROOF_PALETTE]
            light, dark = self._roof_colors[header.group]
            palettes[ROOF_PALETTE] = (roof[0], light, dark, roof[3])
        return tuple(palettes)

    # --- Tuiles et métatuiles -------------------------------------------------

    @cached_property
    def _roof_images(self) -> dict[int, Image.Image]:
        """Groupe de cartes -> tuiles de son toit (data/maps/roofs.asm), pour les groupes qui en ont un."""
        lines = source_lines(self.repo.path("data/maps/roofs.asm"))
        roofs = [line.split()[1] for line in lines if line.startswith("const ROOF_")]
        table = lines[lines.index("MapGroupRoofs:") + 1 : lines.index("Roofs:")]
        groups = [line.split()[1] for line in table if line.startswith("db ")]
        files = [re.sub(r"\.2bpp$", ".png", line.split('"')[1]) for line in lines if line.startswith("INCBIN ")]
        images = {roof: tile_shades(self.repo.path(path)) for roof, path in zip(roofs, files, strict=True)}
        return {group: images[roof] for group, roof in enumerate(groups) if roof != "-1"}

    @cached_property
    def _tileset_images(self) -> dict[str, Image.Image]:
        return {const: tile_shades(tileset.gfx) for const, tileset in self.repo.tilesets.items()}

    def blocks(self, pret_map: PretMap) -> list[Image.Image]:
        header = self.repo.headers[pret_map.const]
        roof = header.group if header.tileset in ROOF_TILESETS and header.group in self._roof_images else None
        key = (header.tileset, self.palettes(header), roof)
        if key not in self._cache:
            self._cache[key] = self._colored_blocks(*key)
        blocks, unusable = self._cache[key]
        if used := sorted(unusable & {*pret_map.blocks, pret_map.border_block}):
            raise ValueError(f"{pret_map.const} : métatuiles {used} faites de tuiles hors du tileset et de la police")
        return blocks

    def _colored_blocks(
        self, tileset_const: str, palettes: tuple[Palette, ...], roof: int | None
    ) -> tuple[list[Image.Image], frozenset[int]]:
        """Métatuiles colorées du tileset, et rang de celles qu'on ne peut pas dessiner : des métatuiles qu'aucune
        carte n'emploie font référence à des tuiles hors du tileset ($ff), qui restent alors vides."""
        tileset = self.repo.tilesets[tileset_const]
        tiles = self._tiles(tileset_const, roof)
        blocks = []
        unusable = set()
        for index in range(tileset.metatile_count()):
            block = Image.new("RGB", (BLOCK_PX, BLOCK_PX))
            for position, tile in enumerate(tileset.metatiles[index * 16 : index * 16 + 16]):
                image = self._tile(tiles, tileset.palettes, palettes, tile)
                if image is None:
                    unusable.add(index)
                else:
                    block.paste(image, self._tile_origin(position))
            blocks.append(block)
        return blocks, frozenset(unusable)

    def _tiles(self, tileset: str, roof: int | None) -> Image.Image:
        """Tuiles du tileset en indices de couleur, avec les tuiles de toit du groupe de la carte."""
        tiles = self._tileset_images[tileset].copy()
        if roof is not None:
            roof_tiles = self._roof_images[roof]
            for index in range(ROOF_LENGTH):
                tile = Image.new("L", (8, 8))
                paint_tile(tile, roof_tiles, index, 0)
                target = ROOF_FIRST_TILE + index
                tiles.paste(tile, ((target % 16) * 8, (target // 16) * 8))
        return tiles

    @staticmethod
    def _tile_origin(position: int) -> tuple[int, int]:
        return (position % 4) * 8, (position // 4) * 8

    def _tile(
        self, tiles: Image.Image, tile_palettes: tuple[str, ...], palettes: tuple[Palette, ...], tile: int
    ) -> Image.Image | None:
        """Tuile 8 × 8 en couleurs ; la tuile espace de la police est de la couleur 0 de la palette TEXT. None pour
        une autre tuile hors du tileset."""
        image = Image.new("P", (8, 8))
        if tile < len(tile_palettes):
            paint_tile(image, tiles, tile, 0)
            palette = palettes[TILE_PALETTES.index(tile_palettes[tile])]
        elif tile == SPACE_TILE:
            palette = palettes[TILE_PALETTES.index("TEXT")]
        else:
            return None
        image.putpalette([channel for color in palette for channel in color])
        return image.convert("RGB")

    # --- Sprites --------------------------------------------------------------

    @cached_property
    def _sprite_palettes(self) -> dict[str, Palette]:
        """Palette de sprite (PAL_OW_RED…) -> 4 couleurs de jour (gfx/overworld/npc_sprites.pal)."""
        consts = [
            line.split()[1]
            for line in source_lines(self.repo.path("constants/sprite_data_constants.asm"))
            if line.startswith("const PAL_OW_")
        ]
        lines = self.repo.path("gfx/overworld/npc_sprites.pal").read_text("utf-8").splitlines()
        start = next(index for index, line in enumerate(lines) if line.strip() == f"; {RENDERED_TIME.lower()}")
        colors = [tuple(_rgb(line.split(";")[0].strip())) for line in lines[start + 1 : start + 1 + len(consts)]]
        return dict(zip(consts, colors, strict=True))

    def write_sprites(self, sprites: set[str], output: Path) -> None:
        for sprite in sorted(sprites):
            overworld = self.repo.sprites[sprite]
            output.mkdir(parents=True, exist_ok=True)
            name = identifier(sprite.removeprefix("SPRITE_"))
            image = sprite_image(overworld.image, self._sprite_palettes[overworld.palette])
            image.save(output / f"{name}.webp", "WEBP", **WEBP_LOSSLESS)
