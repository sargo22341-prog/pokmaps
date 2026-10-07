"""Génération des cartes pixel-art à partir des désassemblages pret.

Pour chaque jeu :
- les villes et routes sont assemblées en une carte du monde (« kanto ») grâce aux connexions entre cartes ;
- chaque carte intérieure accessible (grottes, bâtiments, étages…) est une carte à part ;
- chaque carte affichable est découpée en tuiles de 256 px pour MapCompose, sur plusieurs niveaux de zoom :
  assets/maps/<groupe de versions>/<carte>/<niveau>/<ligne>_<colonne>.webp
  (le dernier niveau est à la taille réelle du jeu, 1 px = 1 pixel Game Boy ; l'application agrandit sans lissage).

Ce module assemble les lignes de la base (cartes, warps, emplacements) ; les personnages, objets et
installations sont dans `maps_characters.py`, le placement et le terrain dans `maps_layout.py`, le rendu des
images dans `maps_render.py`.

Les coordonnées exportées (warps, objets, PNJ, zones) sont en pixels de la carte affichée : celles des villes
et routes sont donc exprimées dans la carte du monde.
"""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .games import GAMES, Game
from .maps_characters import CharacterCuration, ObjectRow, object_rows, read_character_curation
from .maps_layout import WORLD, GameMaps, identifier
from .maps_render import MapRenderer, write_sprites, write_tiles
from .pret import BLOCK_PX, LAST_MAP, PretRepo
from .sources import DATA_DIR, fetch_pret

# Numéro donné à la carte du monde (les cartes pret sont numérotées de 0 à 255).
WORLD_NUMBER = 999
WORLD_NAME_FR = "Kanto"


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
class SpotRow:
    map_const: str
    kind: str  # grass, water ou floor
    x: int
    y: int


@dataclass
class GameMapData:
    """Ce qu'il faut écrire dans la base pour un jeu."""

    maps: list[MapRow]
    areas: list[tuple[str, str]]
    warps: list[WarpRow]
    objects: list[ObjectRow]
    spots: list[SpotRow] = field(default_factory=list)


def export_game(
    game: Game,
    game_maps: GameMaps,
    names: dict[str, str],
    areas: list[tuple[str, str]],
    curation: CharacterCuration,
    output: Path,
) -> GameMapData:
    """Rend les cartes du jeu dans `output` (tuiles et sprites) et renvoie les lignes de la base."""
    repo, placements = game_maps.repo, game_maps.placements
    missing = sorted(const for const in placements if const not in names)
    if missing:
        raise ValueError(f"Nom français manquant dans tools/data/maps.csv : {missing}")
    if output.exists():
        shutil.rmtree(output)

    rows = _display_map_rows(game_maps, names, output)
    warps = _warp_rows(game_maps)
    objects, sprites = object_rows(game, game_maps, curation)
    spots = _spot_rows(game_maps)
    write_sprites(repo, sprites, output / "sprites")
    game_areas = [(const, area) for const, area in areas if const in placements]
    return GameMapData(rows, game_areas, warps, objects, spots)


def _display_map_rows(game_maps: GameMaps, names: dict[str, str], output: Path) -> list[MapRow]:
    maps = game_maps.maps
    rows: list[MapRow] = []
    renderer = MapRenderer(game_maps)
    for const in game_maps.display_maps:
        display = renderer.render(const)
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

    return rows


def _warp_rows(game_maps: GameMaps) -> list[WarpRow]:
    """Warps où le joueur peut se tenir (pret signale les autres « inaccessible »)."""
    maps = game_maps.maps
    warps: list[WarpRow] = []
    for const in sorted(game_maps.placements, key=lambda c: maps[c].number):
        for warp in maps[const].warps:
            if not warp.accessible:
                continue
            target = _warp_target(game_maps, const, warp.target, warp.target_warp)
            target_point = game_maps.point(*target) if target else (None, None)
            warps.append(WarpRow(const, *game_maps.point(const, warp.x, warp.y), target and target[0], *target_point))
    return warps


def _spot_rows(game_maps: GameMaps) -> list[SpotRow]:
    maps = game_maps.maps
    return [
        SpotRow(const, kind, *game_maps.point(const, x, y))
        for const in sorted(game_maps.placements, key=lambda c: maps[c].number)
        for kind, cells in game_maps.spots(const).items()
        for x, y in cells
    ]


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
    names, areas, curation = read_map_names(), read_map_areas(), read_character_curation()
    result = {}
    for game in games:
        game_maps = GameMaps(PretRepo(fetch_pret(cache, game.pret_repo)))
        result[game.version_group] = export_game(game, game_maps, names, areas, curation, output / game.version_group)
    placed = {row.const for data in result.values() for row in data.maps}
    unknown = sorted({const for const in names if const not in placed} | {c for c, _ in areas if c not in placed})
    if unknown:
        raise ValueError(f"Cartes de tools/data/ absentes des jeux : {unknown}")
    if games == GAMES and (unused := curation.unused()):
        raise ValueError(f"Personnages de npc_duplicates.csv ou npc_offers.csv absents des jeux : {unused}")
    return result
