"""Génération des cartes pixel-art à partir des désassemblages pret.

Pour chaque jeu :
- les villes et routes de chaque région sont assemblées en une carte du monde (« kanto », « johto ») grâce aux
  connexions entre cartes ;
- les zones d'un même niveau sont réunies selon map_plans.csv ; les autres intérieurs accessibles et les maisons
  restent des cartes à part ;
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

from .games import GAMES, Game, complete_families
from .maps_characters import ObjectRow, object_rows
from .maps_characters_data import CharacterCuration, read_character_curation
from .maps_layout import GameMaps, identifier, read_layout_curation
from .maps_render import MapRenderer, write_tiles
from .maps_render_gen1 import Gen1Renderer
from .maps_render_gen2 import Gen2Renderer
from .pret import BLOCK_PX, LAST_MAP, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_gen2_wild import roaming_maps
from .pret_reader import open_pret
from .sources import DATA_DIR, fetch_pret

# Zone PokéAPI des Pokémon errants de Johto (Raikou, Entei, Suicune), qui parcourent les cartes de RoamMaps.
GEN2_ROAMING_AREA = "roaming-johto/area"
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


def read_map_areas() -> dict[str, list[tuple[str, str]]]:
    """Famille de cartes -> (constante de carte, zone PokéAPI « lieu/zone »)."""
    areas: dict[str, list[tuple[str, str]]] = {}
    with (DATA_DIR / "map_areas.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            pair = (row["map"], row["location_area"])
            if pair in areas.get(row["family"], []):
                raise ValueError(f"map_areas.csv:{line} : zone en double pour {row['family']} {row['map']}")
            areas.setdefault(row["family"], []).append(pair)
    return areas


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
    is_world: bool = False
    origin: str | None = None
    start: str | None = None


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
    kind: str  # grass, water, floor, tree ou rock (map_spots.SPOT_KINDS)
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
    # Toutes les cases de chaque terrain sauvage, (identifiant de carte, terrain) -> centres en pixels de la carte
    # affichée : un emplacement retouché à la main (map_spots.csv) doit en faire partie dans les jeux ciblés.
    terrain: dict[tuple[str, str], frozenset[tuple[int, int]]] = field(default_factory=dict)


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
    names = names | {const: plan.name for const, plan in game_maps.plans.items()}
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
    game_areas = [(const, area) for const, area in [*areas, *_roaming_areas(game_maps)] if const in placements]
    return GameMapData(rows, game_areas, warps, objects, spots, _terrain(game_maps))


def _roaming_areas(game_maps: GameMaps) -> list[tuple[str, str]]:
    """Cartes que parcourent les Pokémon errants (2e génération), rattachées à la zone PokéAPI des errants."""
    match game_maps.repo:
        case PretRepo():
            return []
        case Gen2PretRepo() as repo:
            return [(const, GEN2_ROAMING_AREA) for const in roaming_maps(repo)]


def _display_map_rows(
    game_maps: GameMaps, names: dict[str, str], map_renderer: MapRenderer, output: Path
) -> list[MapRow]:
    maps = game_maps.maps
    numbers = {region.const: region.number for region in game_maps.game.regions}
    plan_numbers = {const: plan.number for const, plan in game_maps.plans.items()}
    rows: list[MapRow] = []
    for const in game_maps.display_maps:
        display = map_renderer.render(const)
        write_tiles(display, output / identifier(const))
        number = numbers.get(const) or plan_numbers.get(const) or maps[const].number
        start = next((region.start_map for region in game_maps.game.regions if region.const == const), None)
        rows.append(
            MapRow(
                const,
                number,
                names[const],
                None,
                0,
                0,
                display.width,
                display.height,
                display.level_count,
                const in numbers,
                game_maps.parents.get(const) or _plan_origin(game_maps, const),
                start,
            )
        )
    for const, placed in game_maps.placements.items():
        if placed.display == const:
            continue
        pret_map = maps[const]
        width, height = pret_map.width * BLOCK_PX, pret_map.height * BLOCK_PX
        rows.append(
            MapRow(
                const,
                pret_map.number,
                names[const],
                placed.display,
                placed.x,
                placed.y,
                width,
                height,
                0,
                origin=game_maps.parents.get(const),
            )
        )
    return rows


def _plan_origin(game_maps: GameMaps, const: str) -> str | None:
    plan = game_maps.plans.get(const)
    return game_maps.parents[plan.parts[0].map] if plan else None


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


def _terrain(game_maps: GameMaps) -> dict[tuple[str, str], frozenset[tuple[int, int]]]:
    """Centres des cases de chaque terrain sauvage des cartes placées où un Pokémon dessiné ne masque rien."""
    return {
        (identifier(const), kind): frozenset(game_maps.point(const, x, y) for x, y in cells)
        for const in game_maps.placements
        for kind, cells in game_maps.free_cells(const).items()
        if cells
    }


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
        family_names, family_areas = names.get(game.map_family, {}), areas.get(game.map_family, [])
        output_game = output / game.version_group
        result[game.version_group] = export_game(game_maps, family_names, family_areas, curation, output_game)
    for family, version_groups in complete_families(games).items():
        _check_family_used(family, names.get(family, {}), areas.get(family, []), version_groups, result)
        placed = {row.const for group in version_groups for row in result[group].maps}
        if unknown := sorted({part.map for part in layout.plans if part.family == family} - placed):
            raise ValueError(f"map_plans.csv : zones absentes des jeux {family} : {unknown}")
    families, repos = set(complete_families(games)), {game.pret_repo for game in games}
    if unused := curation.unused(families, repos):
        raise ValueError(f"Personnages de npc_duplicates.csv ou npc_offers.csv absents des jeux : {unused}")
    return result


def _check_family_used(
    family: str,
    names: dict[str, str],
    areas: list[tuple[str, str]],
    version_groups: tuple[str, ...],
    result: dict[str, GameMapData],
) -> None:
    """Chaque nom de maps.csv et chaque carte de map_areas.csv de la famille doit servir à l'un de ses jeux."""
    placed = {row.const for group in version_groups for row in result[group].maps}
    if unknown := sorted(set(names) - placed):
        raise ValueError(f"Cartes de tools/data/maps.csv absentes des jeux {family} : {unknown}")
    if unknown := sorted({const for const, _ in areas} - placed):
        raise ValueError(f"Cartes de tools/data/map_areas.csv absentes des jeux {family} : {unknown}")
