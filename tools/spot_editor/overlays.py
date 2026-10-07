"""Calques de l'éditeur : objets, personnages, entrées et Pokémon sauvages dessinés comme dans l'application.

Les tailles et couleurs reprennent celles de ui/map/MapMarkers.kt, à l'échelle de la carte (une case = 16 px),
pour voir où un emplacement chevaucherait un autre élément de la carte finale."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from PIL import Image, ImageDraw

from pokemaps_data.map_spots import Point

from .catalog import EditorMap, MapMark


class Layer(Enum):
    """Calque affichable, avec son libellé dans la fenêtre."""

    WARPS = "Entrées"
    ITEMS = "Objets et objets cachés"
    TRAINERS = "Dresseurs"
    NPCS = "Personnages et installations"
    STATIC_POKEMON = "Pokémon fixes"
    WILD_PREVIEW = "Aperçu des Pokémon sauvages"


_LAYERS = {
    "warp": Layer.WARPS,
    "item": Layer.ITEMS,
    "hidden_item": Layer.ITEMS,
    "trainer": Layer.TRAINERS,
    "pokemon": Layer.STATIC_POKEMON,
    "npc": Layer.NPCS,
    "npc_object": Layer.NPCS,
    "npc_pokemon": Layer.NPCS,
    "vending_machine": Layer.NPCS,
    "prize_vendor": Layer.NPCS,
}
_FACILITIES = frozenset({"vending_machine", "prize_vendor"})
# Constantes de MapMarkers.kt : un pixel d'un sprite de Pokémon vaut POKEMON_RATIO pixel de la carte.
_POKEMON_RATIO = 0.6825
_TILE_PX = 16
_ITEM_PX = 32
_WARP_PX = 9
_BADGE_PX = 8
_HIDDEN_ALPHA = 0.75
_WARP_COLOR = (41, 98, 255, 217)
_HIDDEN_COLOR = (106, 27, 154, 255)
_TRAINER_COLOR = (211, 47, 47, 255)
_FACILITY_COLOR = (0, 137, 123, 255)
_WHITE = (255, 255, 255, 255)


def layer_of(mark: MapMark) -> Layer:
    if mark.kind not in _LAYERS:
        raise ValueError(f"Genre d'objet de carte inconnu de l'éditeur : {mark.kind!r}")
    return _LAYERS[mark.kind]


def wild_preview(points: frozenset[Point], pokemon_ids: list[int]) -> list[tuple[Point, int]]:
    """Un Pokémon du terrain sur chaque emplacement, à tour de rôle : un aperçu de la place prise par les sprites."""
    if not pokemon_ids:
        return []
    return [(point, pokemon_ids[index % len(pokemon_ids)]) for index, point in enumerate(sorted(points))]


class OverlayPainter:
    """Dessine les calques choisis sur l'image d'un lieu, à sa taille native."""

    def __init__(self, assets: Path) -> None:
        self.assets = assets
        # Sprites prêts à coller, par fichier des assets : leur nombre est borné par celui des images générées.
        self._sprites: dict[Path, Image.Image] = {}

    def paint(
        self,
        base: Image.Image,
        editor_map: EditorMap,
        marks: list[MapMark],
        layers: frozenset[Layer],
        wild: list[tuple[Point, int]],
    ) -> Image.Image:
        image = base.copy()
        shown = [mark for mark in marks if layer_of(mark) in layers]
        origin = (editor_map.x, editor_map.y)
        for mark in shown:
            if mark.kind != "warp":
                self._paint_object(image, editor_map.version_group, mark, _local(origin, (mark.x, mark.y)))
        if Layer.WILD_PREVIEW in layers:
            for point, pokemon_id in wild:
                _paste(image, self._pokemon(pokemon_id), _local(origin, point))
        # Les entrées passent au-dessus, comme dans l'application.
        for mark in shown:
            if mark.kind == "warp":
                _paste(image, _disc(_WARP_PX, _WARP_COLOR), _local(origin, (mark.x, mark.y)))
        return image

    def _paint_object(self, image: Image.Image, version_group: str, mark: MapMark, center: Point) -> None:
        if mark.item is not None:
            icon = self._sprite(self.assets / "sprites/items" / f"{mark.item}.webp", _ITEM_PX)
            _paste(image, _faded(icon) if mark.kind == "hidden_item" else icon, center)
        elif mark.kind == "pokemon" and mark.pokemon_id is not None:
            _paste(image, self._pokemon(mark.pokemon_id), center)
        elif mark.sprite is not None:
            path = self.assets / "maps" / version_group / "sprites" / f"{mark.sprite}.webp"
            _paste(image, self._sprite(path, _TILE_PX), center)
        elif mark.kind in _FACILITIES:
            _paste(image, _facility(), center)
        else:
            _paste(image, _disc(_TILE_PX // 2, _WHITE), center)
        if mark.kind == "hidden_item":
            corner = _ITEM_PX // 2 - _BADGE_PX // 2
            _paste(image, _disc(_BADGE_PX, _HIDDEN_COLOR), (center[0] + corner, center[1] + corner))
        elif mark.kind == "trainer":
            _paste(image, _disc(_BADGE_PX, _TRAINER_COLOR), (center[0] + _TILE_PX // 2, center[1] - _TILE_PX // 2))

    def _pokemon(self, pokemon_id: int) -> Image.Image:
        """Sprite fixe du Pokémon, à la taille que lui donne l'application sur la carte."""
        path = self.assets / "sprites/pokemon/static" / f"{pokemon_id}.webp"
        if path not in self._sprites:
            sprite = _load(path)
            size = (max(1, round(sprite.width * _POKEMON_RATIO)), max(1, round(sprite.height * _POKEMON_RATIO)))
            self._sprites[path] = sprite.resize(size, Image.Resampling.NEAREST)
        return self._sprites[path]

    def _sprite(self, path: Path, size: int) -> Image.Image:
        if path not in self._sprites:
            self._sprites[path] = _load(path).resize((size, size), Image.Resampling.NEAREST)
        return self._sprites[path]


def _load(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(f"Image absente des assets : relancer python tools/build_data.py ({path})")
    with Image.open(path) as source:
        return source.convert("RGBA")


def _local(origin: Point, point: Point) -> Point:
    return point[0] - origin[0], point[1] - origin[1]


def _paste(image: Image.Image, sprite: Image.Image, center: Point) -> None:
    """Colle `sprite` centré sur `center`, en coupant ce qui déborde de l'image (alpha_composite le refuse)."""
    x, y = center[0] - sprite.width // 2, center[1] - sprite.height // 2
    left, top = max(0, -x), max(0, -y)
    right, bottom = min(sprite.width, image.width - x), min(sprite.height, image.height - y)
    if left < right and top < bottom:
        image.alpha_composite(sprite, (x + left, y + top), (left, top, right, bottom))


def _faded(sprite: Image.Image) -> Image.Image:
    faded = sprite.copy()
    faded.putalpha(sprite.getchannel("A").point(lambda alpha: round(alpha * _HIDDEN_ALPHA)))
    return faded


def _disc(diameter: int, color: tuple[int, int, int, int]) -> Image.Image:
    disc = Image.new("RGBA", (diameter, diameter))
    ImageDraw.Draw(disc).ellipse((0, 0, diameter - 1, diameter - 1), fill=color, outline=_WHITE)
    return disc


def _facility() -> Image.Image:
    """Installation (distributeur, comptoir des lots) : pastille carrée de la taille d'une case."""
    tile = Image.new("RGBA", (_TILE_PX, _TILE_PX))
    box = (0, 0, _TILE_PX - 1, _TILE_PX - 1)
    ImageDraw.Draw(tile).rounded_rectangle(box, radius=_TILE_PX // 4, fill=_FACILITY_COLOR, outline=_WHITE)
    return tile
