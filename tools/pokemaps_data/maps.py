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

from .games import DECLARED_GAMES, GAMES, Game, PretFormat, complete_families
from .maps_actor_positions import clear_actor_passages
from .maps_characters import ObjectRow, object_rows
from .maps_characters_data import CharacterCuration, read_character_curation
from .maps_layout import GameMaps, identifier, read_layout_curation
from .maps_render import MapRenderer
from .maps_render_gen1 import Gen1Renderer
from .maps_render_gen2 import Gen2Renderer
from .pret import LAST_MAP, PretRepo
from .pret_gen2 import Gen2PretRepo
from .pret_gen2_wild import roaming_maps
from .pret_gen3 import Gen3PretRepo
from .pret_gen3_wild import roaming_maps as gen3_roaming_maps
from .pret_gen4 import Gen4PretRepo
from .pret_hoenn_caves import moving_cave_areas
from .pret_reader import open_pret
from .sources import DATA_DIR, fetch_pret
from .story_events import StoryEvents

# Zone PokéAPI des errants propre à chaque famille de cartes.
ROAMING_AREAS = {
    "gold-silver-crystal": "roaming-johto/area",
    "ruby-sapphire-emerald": "roaming-hoenn/area",
    "firered-leafgreen": "roaming-kanto/area",
}
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


def read_map_areas(version_group: str | None = None) -> dict[str, list[tuple[str, str]]]:
    """Famille de cartes -> (constante de carte, zone PokéAPI « lieu/zone »)."""
    areas: dict[str, list[tuple[str, str]]] = {}
    entries: list[tuple[str, str, str, str]] = []
    families = {game.version_group: game.map_family for game in DECLARED_GAMES}
    with (DATA_DIR / "map_areas.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            scope = row.get("version_group") or ""
            entry = (row["family"], row["map"], row["location_area"], scope)
            required = ("family", "map", "location_area", "note")
            if (
                None in row
                or any(row.get(key) is None for key in required)
                or entry in entries
                or (scope and families.get(scope) != row["family"])
            ):
                raise ValueError(f"map_areas.csv:{line} : colonnes, doublon ou groupe de versions invalide : {row}")
            entries.append(entry)
    overrides = {(family, const) for family, const, _, scope in entries if scope and scope == version_group}
    for family, const, key, scope in entries:
        if version_group is not None and (
            (scope and scope != version_group) or (not scope and (family, const) in overrides)
        ):
            continue
        pair = (const, key)
        if pair not in areas.get(family, []):
            areas.setdefault(family, []).append(pair)
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
    version: str | None = None  # seule version du groupe où la carte existe, None pour toutes


# Passages qui ne sont pas des warps du jeu : plongée scriptée, téléphérique, apparition de l'Île Mirage et
# entrée d'une Base Secrète. None pour une porte, un escalier ou une entrée de grotte.
WARP_KINDS = frozenset({"dive", "cable_car", "mirage", "secret_base"})


@dataclass
class WarpRow:
    map_const: str
    x: int
    y: int
    target: str | None
    target_x: int | None
    target_y: int | None
    kind: str | None = None

    def __post_init__(self) -> None:
        if self.kind is not None and self.kind not in WARP_KINDS:
            raise ValueError(f"Type de passage inconnu : {self.kind}")


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
    # Les aperçus partiels n'exportent pas encore les personnages ; leurs noms se valident dans les sources.
    characters_complete: bool = True
    story: StoryEvents | None = None


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
    rows = display_map_rows(game_maps, names, map_renderer, output)
    warps = _warp_rows(game_maps)
    objects, sprites = object_rows(game_maps, curation)
    objects = clear_actor_passages(game_maps, objects)
    spots = _spot_rows(game_maps)
    map_renderer.write_sprites(sprites, output / "sprites")
    game_areas = [(const, area) for const, area in [*areas, *roaming_areas(game_maps)] if const in placements]
    return GameMapData(rows, game_areas, warps, objects, spots, _terrain(game_maps))


def roaming_areas(game_maps: GameMaps) -> list[tuple[str, str]]:
    """Routes du moteur rattachées à la zone PokéAPI des errants de leur famille."""
    match game_maps.repo:
        case PretRepo():
            return []
        case Gen2PretRepo() as repo:
            routes = roaming_maps(repo)
        case Gen3PretRepo() as repo:
            routes = gen3_roaming_maps(repo)
    areas = [(const, ROAMING_AREAS[game_maps.game.map_family]) for const in routes]
    if isinstance(game_maps.repo, Gen3PretRepo):
        areas.extend(moving_cave_areas(game_maps.repo))
    return areas


def display_map_rows(
    game_maps: GameMaps, names: dict[str, str], map_renderer: MapRenderer, output: Path
) -> list[MapRow]:
    maps = game_maps.maps
    numbers = game_maps.world_numbers
    plan_numbers = {const: plan.number for const, plan in game_maps.plans.items()}
    rows: list[MapRow] = []
    for const in game_maps.display_maps:
        display = map_renderer.write_display(const, output / identifier(const))
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
                _display_version(game_maps, const),
            )
        )
    for const, placed in game_maps.placements.items():
        if placed.display == const:
            continue
        pret_map = maps[const]
        width, height = pret_map.width * game_maps.block_px, pret_map.height * game_maps.block_px
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
                version=game_maps.version_maps.get(const),
            )
        )
    return rows


def _display_version(game_maps: GameMaps, const: str) -> str | None:
    """Version d'une carte affichée ; un plan n'appartient à une version que si toutes ses zones lui appartiennent."""
    plan = game_maps.plans.get(const)
    if plan is None:
        return game_maps.version_maps.get(const)
    versions = {game_maps.version_maps.get(part.map) for part in plan.parts}
    if len(versions) != 1:
        raise ValueError(f"{const} : plan mêlant des zones de versions différentes : {sorted(map(str, versions))}")
    return versions.pop()


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
        if game.pret_format == PretFormat.GEN3:
            from .maps_export_gen3 import export_game as export_gen3_game

            result[game.version_group] = export_gen3_game(cache, output / game.version_group, game)
            continue
        if game.pret_format == PretFormat.GEN4:
            raise ValueError(f"{game.version_group} : cartes DS sans rendu, à construire avant d'activer le jeu")
        repo = open_pret(game, fetch_pret(cache, game.pret_repo))
        if isinstance(repo, Gen4PretRepo):
            raise ValueError(f"{game.version_group} : lecteur DS inattendu pour des cartes en tuiles")
        game_maps = GameMaps(repo, game, layout)
        family_names = names.get(game.map_family, {})
        family_areas = read_map_areas(game.version_group).get(game.map_family, [])
        output_game = output / game.version_group
        result[game.version_group] = export_game(game_maps, family_names, family_areas, curation, output_game)
    for family, version_groups in complete_families(games).items():
        _check_family_used(family, names.get(family, {}), areas.get(family, []), version_groups, result)
        placed = {row.const for group in version_groups for row in result[group].maps}
        if unknown := sorted({part.map for part in layout.plans if part.family == family} - placed):
            raise ValueError(f"map_plans.csv : zones absentes des jeux {family} : {unknown}")
    legacy = tuple(game for game in games if game.pret_format != PretFormat.GEN3)
    families, repos = set(complete_families(legacy)), {game.pret_repo for game in legacy}
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
