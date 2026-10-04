"""Génération des cartes pixel-art à partir des désassemblages pret.

Pour chaque jeu :
- les villes et routes sont assemblées en une carte du monde (« kanto ») grâce aux connexions entre cartes ;
- chaque carte intérieure accessible (grottes, bâtiments, étages…) est une carte à part ;
- chaque carte affichable est découpée en tuiles de 256 px pour MapCompose, sur plusieurs niveaux de zoom :
  assets/maps/<groupe de versions>/<carte>/<niveau>/<ligne>_<colonne>.webp
  (le dernier niveau est à la taille réelle du jeu, 1 px = 1 pixel Game Boy ; l'application agrandit sans lissage).

Les couleurs sont celles du Super Game Boy : chaque ville a sa palette, les routes partagent la même, les
bâtiments prennent celle de la ville ou de la route où ils se trouvent.

Les coordonnées exportées (warps, objets, PNJ, zones) sont en pixels de la carte affichée : celles des villes
et routes sont donc exprimées dans la carte du monde.
"""

from __future__ import annotations

import csv
import math
import shutil
from collections import deque
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

from PIL import Image

from .games import GAMES, Game
from .pret import BLOCK_PX, LAST_MAP, STEP_PX, TILE_PX, PretMap, PretRepo
from .sources import fetch_pret

TILE_SIZE = 256
# Blocs de bordure dessinés autour des villes et routes (le jeu en affiche 4 à 5 au bord de l'écran).
BORDER_MARGIN = 4
WORLD = "KANTO"
# Numéro donné à la carte du monde (les cartes pret sont numérotées de 0 à 255).
WORLD_NUMBER = 999
WORLD_NAME_FR = "Kanto"
START_MAP = "PALLET_TOWN"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Objets dont l'identifiant PokéAPI ne se déduit pas de la constante pret.
ITEM_ALIASES = {"ELIXER": "elixir", "MAX_ELIXER": "max-elixir", "X_SPECIAL": "x-sp-atk"}

# Palettes particulières (cf. SetPal_Overworld dans engine/gfx/palettes.asm).
CEMETERY_TILESET, CAVERN_TILESET = "CEMETERY", "CAVERN"
CAVE_MAPS = frozenset({"CERULEAN_CAVE_2F", "CERULEAN_CAVE_B1F", "CERULEAN_CAVE_1F", "BRUNOS_ROOM"})
LORELEI_MAP = "LORELEIS_ROOM"


def identifier(const: str) -> str:
    return const.lower().replace("_", "-")


def item_identifier(repo: PretRepo, const: str) -> str:
    return repo.machines.get(const) or ITEM_ALIASES.get(const) or identifier(const)


@dataclass
class Placed:
    """Position d'une carte pret dans la carte affichée qui la contient."""

    display: str  # constante de la carte affichée (WORLD pour les villes et routes)
    x: int  # en pixels
    y: int


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


class GameMaps:
    """Cartes d'un jeu : sélection, placement et rendu."""

    def __init__(self, repo: PretRepo) -> None:
        self.repo = repo
        self.maps = repo.maps

    # --- Sélection et placement -------------------------------------------

    @cached_property
    def world_blocks(self) -> dict[str, tuple[int, int]]:
        """Position (en blocs) de chaque ville et route dans la carte du monde, via les connexions."""
        positions = {START_MAP: (0, 0)}
        queue = deque([START_MAP])
        while queue:
            current = self.maps[queue.popleft()]
            x, y = positions[current.const]
            for connection in current.connections:
                target = self.maps[connection.target]
                position = {
                    "north": (x + connection.offset, y - target.height),
                    "south": (x + connection.offset, y + current.height),
                    "west": (x - target.width, y + connection.offset),
                    "east": (x + current.width, y + connection.offset),
                }[connection.direction]
                if target.const not in positions:
                    positions[target.const] = position
                    queue.append(target.const)
                elif positions[target.const] != position:
                    raise ValueError(f"Connexion incohérente {current.const} -> {target.const}")
        min_x = min(x for x, _ in positions.values())
        min_y = min(y for _, y in positions.values())
        outdoor = {const for const, pret_map in self.maps.items() if pret_map.is_outdoor}
        if outdoor - positions.keys():
            raise ValueError(f"Cartes extérieures non reliées à {START_MAP} : {sorted(outdoor - positions.keys())}")
        return {const: (x - min_x, y - min_y) for const, (x, y) in positions.items()}

    @cached_property
    def world_size(self) -> tuple[int, int]:
        """Taille de la carte du monde, en blocs."""
        width = max(x + self.maps[const].width for const, (x, _) in self.world_blocks.items())
        height = max(y + self.maps[const].height for const, (_, y) in self.world_blocks.items())
        return width, height

    @cached_property
    def indoor_parents(self) -> dict[str, str]:
        """Cartes intérieures accessibles depuis l'extérieur (par les warps) -> ville ou route d'origine."""
        parents: dict[str, str] = {}
        queue = deque()
        for const in sorted(self.world_blocks, key=lambda c: self.maps[c].number):
            queue.append((const, const))
        while queue:
            const, origin = queue.popleft()
            for warp in self.maps[const].warps:
                target = warp.target
                if target == LAST_MAP or target not in self.maps or self.maps[target].is_outdoor:
                    continue
                if target not in parents:
                    parents[target] = origin
                    queue.append((target, origin))
        return parents

    @cached_property
    def placements(self) -> dict[str, Placed]:
        placed = {const: Placed(WORLD, x * BLOCK_PX, y * BLOCK_PX) for const, (x, y) in self.world_blocks.items()}
        placed |= {const: Placed(const, 0, 0) for const in self.indoor_parents}
        return placed

    @property
    def display_maps(self) -> list[str]:
        indoor = sorted(self.indoor_parents, key=lambda c: self.maps[c].number)
        return [WORLD, *indoor]

    # --- Palettes -------------------------------------------------------------

    def palette_name(self, const: str) -> str:
        pret_map = self.maps[const]
        if pret_map.tileset == CEMETERY_TILESET:
            return "PAL_GRAYMON"
        if pret_map.tileset == CAVERN_TILESET or const in CAVE_MAPS:
            return "PAL_CAVE"
        if const == LORELEI_MAP:
            return "PAL_PALLET"
        if not pret_map.is_outdoor:
            pret_map = self.maps[self.indoor_parents[const]]
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

    def _blocks(self, tileset: str, palette: str, cache: dict) -> list[Image.Image]:
        key = (tileset, palette)
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

    def _paint(self, canvas: Image.Image, pret_map: PretMap, origin: tuple[int, int], cache: dict) -> None:
        blocks = self._blocks(pret_map.tileset, self.palette_name(pret_map.const), cache)
        for y in range(pret_map.height):
            for x in range(pret_map.width):
                position = (origin[0] + x * BLOCK_PX, origin[1] + y * BLOCK_PX)
                canvas.paste(blocks[pret_map.block(x, y)], position)

    def render(self, const: str, cache: dict) -> DisplayMap:
        if const == WORLD:
            return self._render_world(cache)
        pret_map = self.maps[const]
        width, height = pret_map.width * BLOCK_PX, pret_map.height * BLOCK_PX
        canvas = Image.new("RGB", (width, height))
        self._paint(canvas, pret_map, (0, 0), cache)
        return DisplayMap(const, width, height, level_count(width, height), canvas)

    def _render_world(self, cache: dict) -> DisplayMap:
        columns, rows = self.world_size
        canvas = Image.new("RGBA", (columns * BLOCK_PX, rows * BLOCK_PX))
        owner: list[list[str | None]] = [[None] * columns for _ in range(rows)]
        for const, (bx, by) in self.world_blocks.items():
            pret_map = self.maps[const]
            self._paint(canvas, pret_map, (bx * BLOCK_PX, by * BLOCK_PX), cache)
            for y in range(pret_map.height):
                for x in range(pret_map.width):
                    owner[by + y][bx + x] = const
        # Autour des cartes : le bloc de bordure de la carte la plus proche, sur la largeur visible à l'écran
        # dans le jeu. Au-delà, la carte du monde reste transparente.
        rects = [(*self.world_blocks[const], self.maps[const]) for const in self.world_blocks]

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
                blocks = self._blocks(pret_map.tileset, self.palette_name(pret_map.const), cache)
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


# --- Données relues à la main ---------------------------------------------------


def read_map_names() -> dict[str, str]:
    with (DATA_DIR / "maps.csv").open(encoding="utf-8", newline="") as handle:
        return {row["map"]: row["name_fr"] for row in csv.DictReader(handle)}


def read_map_areas() -> list[tuple[str, str]]:
    """(constante de carte, zone PokéAPI « lieu/zone »)."""
    with (DATA_DIR / "map_areas.csv").open(encoding="utf-8", newline="") as handle:
        return [(row["map"], row["location_area"]) for row in csv.DictReader(handle)]


# --- Export -----------------------------------------------------------------------


@dataclass
class MapRow:
    const: str
    number: int
    name_fr: str
    parent: str | None
    x: int
    y: int
    width: int
    height: int
    level_count: int


@dataclass
class WarpRow:
    map_const: str
    x: int
    y: int
    target: str | None
    target_x: int | None
    target_y: int | None


@dataclass
class ObjectRow:
    map_const: str
    kind: str
    x: int
    y: int
    sprite: str | None
    item: str | None  # identifiant PokéAPI
    pokemon: str | None  # identifiant PokéAPI
    level: int | None
    trainer_class: str | None


@dataclass
class GameMapData:
    """Ce qu'il faut écrire dans la base pour un jeu."""

    maps: list[MapRow]
    areas: list[tuple[str, str]]
    warps: list[WarpRow]
    objects: list[ObjectRow]


def export_game(game_maps: GameMaps, names: dict[str, str], areas: list[tuple[str, str]], output: Path) -> GameMapData:
    """Rend les cartes du jeu dans `output` (tuiles et sprites) et renvoie les lignes de la base."""
    repo, maps, placements = game_maps.repo, game_maps.maps, game_maps.placements
    missing = sorted(const for const in placements if const not in names)
    if missing:
        raise ValueError(f"Nom français manquant dans tools/data/maps.csv : {missing}")
    if output.exists():
        shutil.rmtree(output)

    rows: list[MapRow] = []
    cache: dict = {}
    for const in game_maps.display_maps:
        display = game_maps.render(const, cache)
        write_tiles(display, output / identifier(const))
        name, number = (WORLD_NAME_FR, WORLD_NUMBER) if const == WORLD else (names[const], maps[const].number)
        rows.append(MapRow(const, number, name, None, 0, 0, display.width, display.height, display.level_count))
    for const, (bx, by) in sorted(game_maps.world_blocks.items(), key=lambda item: maps[item[0]].number):
        pret_map = maps[const]
        rows.append(
            MapRow(
                const,
                pret_map.number,
                names[const],
                WORLD,
                bx * BLOCK_PX,
                by * BLOCK_PX,
                pret_map.width * BLOCK_PX,
                pret_map.height * BLOCK_PX,
                0,
            )
        )

    def point(const: str, x: int, y: int) -> tuple[int, int]:
        placed = placements[const]
        return placed.x + x * STEP_PX + STEP_PX // 2, placed.y + y * STEP_PX + STEP_PX // 2

    warps: list[WarpRow] = []
    objects: list[ObjectRow] = []
    sprites: set[str] = set()
    for const in sorted(placements, key=lambda c: maps[c].number):
        pret_map = maps[const]
        for warp in pret_map.warps:
            target = _warp_target(game_maps, const, warp.target, warp.target_warp)
            target_point = point(*target) if target else (None, None)
            warps.append(WarpRow(const, *point(const, warp.x, warp.y), target and target[0], *target_point))
        for obj in pret_map.objects:
            if not (0 <= obj.x < pret_map.width * 2 and 0 <= obj.y < pret_map.height * 2):
                continue  # hors de la carte, donc inaccessible (ex. une Pépite cachée de l'entrée du Parc Safari)
            if obj.sprite:
                sprites.add(obj.sprite)
            objects.append(
                ObjectRow(
                    const,
                    obj.kind,
                    *point(const, obj.x, obj.y),
                    obj.sprite and identifier(obj.sprite.removeprefix("SPRITE_")),
                    obj.item and item_identifier(repo, obj.item),
                    obj.pokemon and identifier(obj.pokemon),
                    obj.level,
                    obj.trainer_class and identifier(obj.trainer_class.removeprefix("OPP_")),
                )
            )
    write_sprites(repo, sprites, output / "sprites")
    game_areas = [(const, area) for const, area in areas if const in placements]
    return GameMapData(rows, game_areas, warps, objects)


def _warp_target(game_maps: GameMaps, source: str, target: str, number: int) -> tuple[str, int, int] | None:
    """Carte et position d'arrivée d'un warp. LAST_MAP : la carte dont le warp `number` mène à `source`."""
    maps, placements = game_maps.maps, game_maps.placements
    if target == LAST_MAP:
        candidates = [
            const
            for const in sorted(placements, key=lambda c: (not maps[c].is_outdoor, maps[c].number))
            if len(maps[const].warps) >= number and maps[const].warps[number - 1].target == source
        ]
        if not candidates:
            return None
        target = candidates[0]
    if target not in placements or len(maps[target].warps) < number:
        return None
    arrival = maps[target].warps[number - 1]
    return target, arrival.x, arrival.y


def build_maps(cache: Path, output: Path, games: tuple[Game, ...] = GAMES) -> dict[str, GameMapData]:
    """Génère les cartes de chaque jeu dans `output/<groupe de versions>`. Renvoie les données par groupe."""
    names, areas = read_map_names(), read_map_areas()
    result = {}
    for game in games:
        game_maps = GameMaps(PretRepo(fetch_pret(cache, game.pret_repo)))
        result[game.version_group] = export_game(game_maps, names, areas, output / game.version_group)
    placed = {row.const for data in result.values() for row in data.maps}
    unknown = sorted({const for const in names if const not in placed} | {c for c, _ in areas if c not in placed})
    if unknown:
        raise ValueError(f"Cartes de tools/data/ absentes des jeux : {unknown}")
    return result
