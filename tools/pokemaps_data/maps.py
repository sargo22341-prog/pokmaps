"""Génération des cartes pixel-art à partir des désassemblages pret.

Pour chaque jeu :
- les villes et routes sont assemblées en une carte du monde (« kanto ») grâce aux connexions entre cartes ;
- chaque carte intérieure accessible (grottes, bâtiments, étages…) est une carte à part ;
- chaque carte affichable est découpée en tuiles de 256 px pour MapCompose, sur plusieurs niveaux de zoom :
  assets/maps/<groupe de versions>/<carte>/<niveau>/<ligne>_<colonne>.webp
  (le dernier niveau est à la taille réelle du jeu, 1 px = 1 pixel Game Boy ; l'application agrandit sans lissage).

Ce module assemble les lignes de la base (cartes, warps, objets, emplacements) ; le placement et le terrain
sont dans `maps_layout.py`, le rendu des images dans `maps_render.py`.

Les coordonnées exportées (warps, objets, PNJ, zones) sont en pixels de la carte affichée : celles des villes
et routes sont donc exprimées dans la carte du monde.
"""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .games import GAMES, Game
from .maps_layout import WORLD, GameMaps, identifier
from .maps_render import MapRenderer, write_sprites, write_tiles
from .pret import BLOCK_PX, GYM_LEADERS, LAST_MAP, STEP_PX, NpcOffer, PretRepo
from .sources import fetch_pret

# Numéro donné à la carte du monde (les cartes pret sont numérotées de 0 à 255).
WORLD_NUMBER = 999
WORLD_NAME_FR = "Kanto"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Objets dont l'identifiant PokéAPI ne se déduit pas de la constante pret.
ITEM_ALIASES = {
    "ELIXER": "elixir",
    "MAX_ELIXER": "max-elixir",
    "X_SPECIAL": "x-sp-atk",
    "PARLYZ_HEAL": "paralyze-heal",
    "S_S_TICKET": "ss-ticket",
    "X_DEFEND": "x-defense",
}

# Classes de dresseurs dont l'équipe dépend du starter choisi (fixée par le script, pas par la carte).
STARTER_DEPENDENT_TRAINERS = frozenset({"RIVAL1", "RIVAL2", "RIVAL3"})


def item_identifier(repo: PretRepo, const: str) -> str:
    return repo.machines.get(const) or ITEM_ALIASES.get(const) or identifier(const)


# --- Données relues à la main ---------------------------------------------------


@dataclass(frozen=True)
class CharacterNames:
    """Noms affichés des dresseurs (par classe) et des personnages (par sprite), identifiants PokéAPI."""

    trainers: dict[str, str]
    characters: dict[str, str]

    def trainer(self, trainer_class: str) -> str:
        if trainer_class not in self.trainers:
            raise ValueError(f"Classe de dresseur sans nom français : {trainer_class} (tools/data/trainer_classes.csv)")
        return self.trainers[trainer_class]

    def character(self, sprite: str | None) -> str:
        if sprite not in self.characters:
            raise ValueError(f"Personnage sans nom français : sprite {sprite} (tools/data/npc_names.csv)")
        return self.characters[sprite]


def read_map_names() -> dict[str, str]:
    with (DATA_DIR / "maps.csv").open(encoding="utf-8", newline="") as handle:
        return {row["map"]: row["name_fr"] for row in csv.DictReader(handle)}


def read_character_names() -> CharacterNames:
    """Noms français des classes de dresseurs et des personnages (d'après leur sprite)."""
    with (DATA_DIR / "trainer_classes.csv").open(encoding="utf-8", newline="") as handle:
        trainers = {row["trainer_class"]: row["name_fr"] for row in csv.DictReader(handle)}
    with (DATA_DIR / "npc_names.csv").open(encoding="utf-8", newline="") as handle:
        characters = {row["sprite"]: row["name_fr"] for row in csv.DictReader(handle)}
    return CharacterNames(trainers, characters)


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
    # Équipe d'un dresseur : (Pokémon, niveau, attaques), identifiants PokéAPI.
    party: list[tuple[str, int, tuple[str, ...]]] = field(default_factory=list)
    # Dons, ventes et échanges du personnage (identifiants PokéAPI).
    offers: list[NpcOffer] = field(default_factory=list)


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


def export_game(game_maps: GameMaps, names: dict[str, str], areas: list[tuple[str, str]], output: Path) -> GameMapData:
    """Rend les cartes du jeu dans `output` (tuiles et sprites) et renvoie les lignes de la base."""
    repo, placements = game_maps.repo, game_maps.placements
    missing = sorted(const for const in placements if const not in names)
    if missing:
        raise ValueError(f"Nom français manquant dans tools/data/maps.csv : {missing}")
    if output.exists():
        shutil.rmtree(output)

    rows = _display_map_rows(game_maps, names, output)
    warps, objects, sprites = _placed_map_rows(game_maps)
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


def _placed_map_rows(game_maps: GameMaps) -> tuple[list[WarpRow], list[ObjectRow], set[str]]:
    repo, maps, placements = game_maps.repo, game_maps.maps, game_maps.placements

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
            trainer_class = obj.trainer_class and obj.trainer_class.removeprefix("OPP_")
            party = []
            if trainer_class and trainer_class not in STARTER_DEPENDENT_TRAINERS:
                party = [
                    (identifier(mon.species), mon.level, tuple(identifier(move) for move in mon.moves))
                    for mon in repo.trainer_parties.get((trainer_class, obj.trainer_number or 0), [])
                ]
            offers = repo.npc_offers(obj.text)
            if trainer_class in GYM_LEADERS:
                offers += [offer for offer in repo.leader_gifts(pret_map.label) if offer not in offers]
            objects.append(
                ObjectRow(
                    const,
                    obj.kind,
                    *point(const, obj.x, obj.y),
                    obj.sprite and identifier(obj.sprite.removeprefix("SPRITE_")),
                    obj.item and item_identifier(repo, obj.item),
                    obj.pokemon and identifier(obj.pokemon),
                    obj.level,
                    trainer_class and identifier(trainer_class),
                    party,
                    [_offer_identifiers(repo, offer) for offer in offers],
                )
            )
    return warps, objects, sprites


def _spot_rows(game_maps: GameMaps) -> list[SpotRow]:
    maps, placements = game_maps.maps, game_maps.placements

    def point(const: str, x: int, y: int) -> tuple[int, int]:
        placed = placements[const]
        return placed.x + x * STEP_PX + STEP_PX // 2, placed.y + y * STEP_PX + STEP_PX // 2

    return [
        SpotRow(const, kind, *point(const, x, y))
        for const in sorted(placements, key=lambda c: maps[c].number)
        for kind, cells in game_maps.spots(const).items()
        for x, y in cells
    ]


def _offer_identifiers(repo: PretRepo, offer: NpcOffer) -> NpcOffer:
    """Offre avec les identifiants PokéAPI à la place des constantes pret."""
    return NpcOffer(
        offer.kind,
        offer.item and item_identifier(repo, offer.item),
        offer.pokemon and identifier(offer.pokemon),
        offer.quantity,
        offer.price,
        offer.wanted and identifier(offer.wanted),
    )


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
