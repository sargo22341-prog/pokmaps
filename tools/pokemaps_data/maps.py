"""Génération des cartes pixel-art à partir des désassemblages pret.

Pour chaque jeu :
- les villes et routes de chaque région sont assemblées en une carte du monde (« kanto », « johto ») grâce aux
  connexions entre cartes ;
- chaque carte intérieure accessible (grottes, bâtiments, étages…), et chaque ville ou route hors d'une carte du
  monde, est une carte à part ;
- chaque carte affichable est découpée en tuiles de 256 px pour MapCompose, sur plusieurs niveaux de zoom :
  assets/maps/<groupe de versions>/<carte>/<niveau>/<ligne>_<colonne>.webp
  (le dernier niveau est à la taille réelle du jeu, 1 px = 1 pixel Game Boy ; l'application agrandit sans lissage).

Ce module assemble les lignes de la base (cartes, warps, emplacements) ; les personnages, objets et
installations sont dans `maps_characters.py`, le placement dans `maps_layout.py`, le terrain dans
`maps_terrain.py`, le rendu des images dans `maps_render*.py`.

Les coordonnées exportées (warps, objets, PNJ, zones) sont en pixels de la carte affichée : celles des villes
et routes sont donc exprimées dans la carte du monde de leur région.
"""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .games import GAMES, Game, map_families
from .maps_characters import CharacterCuration, ObjectRow, object_rows, read_character_curation
from .maps_layout import GameMaps, identifier, read_layout_curation
from .maps_render import MapRenderer, write_tiles
from .maps_render_gen1 import Gen1Renderer
from .maps_render_gen2 import Gen2Renderer
from .pret import BLOCK_PX, LAST_MAP, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_reader import open_pret
from .sources import DATA_DIR, fetch_pret

# Numéro de warp de la 2e génération : « le warp par lequel on est arrivé », celui de la carte d'arrivée qui
# ramène à la carte de départ (ascenseurs, M/S Aquaria).
RETURN_WARP = -1


def read_map_names() -> dict[str, dict[str, str]]:
    """Famille de cartes -> constante de carte (ou de carte du monde) -> nom français."""
    names: dict[str, dict[str, str]] = {}
    with (DATA_DIR / "maps.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            family = names.setdefault(row["family"], {})
            if row["map"] in family:
                raise ValueError(f"maps.csv:{line} : nom en double pour {row['family']} {row['map']}")
            if not row["name_fr"].strip():
                raise ValueError(f"maps.csv:{line} : nom vide pour {row['family']} {row['map']}")
            family[row["map"]] = row["name_fr"]
    return names


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


def renderer(game_maps: GameMaps) -> MapRenderer:
    """Rendu des cartes du jeu, d'après le format de ses sources pret."""
    match game_maps.repo:
        case PretRepo():
            return Gen1Renderer(game_maps, game_maps.repo)
        case Gen2PretRepo():
            return Gen2Renderer(game_maps, game_maps.repo)


def export_game(
    game_maps: GameMaps,
    names: dict[str, str],
    areas: list[tuple[str, str]],
    curation: CharacterCuration,
    output: Path,
) -> GameMapData:
    """Rend les cartes du jeu dans `output` (tuiles et sprites) et renvoie les lignes de la base."""
    placements = game_maps.placements
    named = [*placements, *(region.const for region in game_maps.game.regions)]
    if missing := sorted(const for const in named if const not in names):
        raise ValueError(f"Nom français manquant dans tools/data/maps.csv : {missing}")
    if output.exists():
        shutil.rmtree(output)

    map_renderer = renderer(game_maps)
    rows = _display_map_rows(game_maps, names, map_renderer, output)
    warps = _warp_rows(game_maps)
    objects, sprites = object_rows(game_maps, curation)
    spots = _spot_rows(game_maps)
    map_renderer.write_sprites(sprites, output / "sprites")
    game_areas = [(const, area) for const, area in areas if const in placements]
    return GameMapData(rows, game_areas, warps, objects, spots)


def _display_map_rows(
    game_maps: GameMaps, names: dict[str, str], map_renderer: MapRenderer, output: Path
) -> list[MapRow]:
    maps = game_maps.maps
    numbers = {region.const: region.number for region in game_maps.game.regions}
    rows: list[MapRow] = []
    for const in game_maps.display_maps:
        display = map_renderer.render(const)
        write_tiles(display, output / identifier(const))
        number = numbers[const] if const in numbers else maps[const].number
        rows.append(MapRow(const, number, names[const], None, 0, 0, display.width, display.height, display.level_count))
    for region, blocks in game_maps.world_blocks.items():
        for const, (bx, by) in sorted(blocks.items(), key=lambda item: maps[item[0]].number):
            pret_map = maps[const]
            width, height = pret_map.width * BLOCK_PX, pret_map.height * BLOCK_PX
            rows.append(
                MapRow(const, pret_map.number, names[const], region, bx * BLOCK_PX, by * BLOCK_PX, width, height, 0)
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
    """Carte et position d'arrivée d'un warp.

    LAST_MAP (1re génération) : la carte dont le warp `number` mène à `source`. RETURN_WARP (2e génération) : le warp
    de `target` qui ramène à `source`, s'il n'y en a qu'un ; sinon l'arrivée dépend d'où l'on vient."""
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
    if target not in placements:
        return None
    if number == RETURN_WARP:
        if target == source:
            return None  # sortie vers la carte d'où l'on vient (étage des Centres Pokémon) : elle dépend du joueur
        back = [warp for warp in maps[target].warps if warp.target == source]
        return (target, back[0].x, back[0].y) if len(back) == 1 else None
    if len(maps[target].warps) < number:
        return None
    arrival = maps[target].warps[number - 1]
    return target, arrival.x, arrival.y


def build_maps(cache: Path, output: Path, games: tuple[Game, ...] = GAMES) -> dict[str, GameMapData]:
    """Génère les cartes de chaque jeu dans `output/<groupe de versions>`. Renvoie les données par groupe."""
    names, areas, curation = read_map_names(), read_map_areas(), read_character_curation()
    layout = read_layout_curation()
    result = {}
    for game in games:
        game_maps = GameMaps(open_pret(game, fetch_pret(cache, game.pret_repo)), game, layout)
        family_names = names.get(game.map_family, {})
        result[game.version_group] = export_game(game_maps, family_names, areas, curation, output / game.version_group)
    _check_names_used(games, names, result)
    if games == GAMES:
        placed = {row.const for data in result.values() for row in data.maps}
        if unknown := sorted({c for c, _ in areas if c not in placed}):
            raise ValueError(f"Cartes de tools/data/map_areas.csv absentes des jeux : {unknown}")
        if unused := curation.unused():
            raise ValueError(f"Personnages de npc_duplicates.csv ou npc_offers.csv absents des jeux : {unused}")
    return result


def _check_names_used(
    games: tuple[Game, ...], names: dict[str, dict[str, str]], result: dict[str, GameMapData]
) -> None:
    """Chaque nom de maps.csv d'une famille dont tous les jeux sont construits doit servir à l'un d'eux."""
    families = map_families((*GAMES, *(game for game in games if game not in GAMES)))
    built = {game.version_group for game in games}
    for family, version_groups in families.items():
        if not set(version_groups) <= built:
            continue
        placed = {row.const for group in version_groups for row in result[group].maps}
        if unknown := sorted(set(names.get(family, {})) - placed):
            raise ValueError(f"Cartes de tools/data/maps.csv absentes des jeux {family} : {unknown}")
