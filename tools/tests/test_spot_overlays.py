"""Calques et terrains de l'éditeur d'emplacements : ce qu'il dessine et les terrains qu'il propose."""

from pathlib import Path

import pytest
from PIL import Image

from spot_editor.catalog import EditorCatalog, EditorMap, Family, MapMark
from spot_editor.overlays import Layer, OverlayPainter, layer_of, wild_preview
from spot_editor.terrain import WildTerrains

from .conftest import CACHE

ROOM = EditorMap("red-blue-yellow", "room", "Salle", "red-blue", (1,), "room", 0, 0, 64, 64)
FAMILY = Family("red-blue-yellow", "Rouge, Bleu et Jaune", ("red-blue", "yellow"))


def mark(kind: str, x: int = 32, y: int = 32, sprite: str | None = None) -> MapMark:
    return MapMark(kind, x, y, sprite, None, None)


def test_every_object_kind_has_a_layer() -> None:
    assert layer_of(mark("warp")) is Layer.WARPS
    assert layer_of(mark("hidden_item")) is Layer.ITEMS
    assert layer_of(mark("trainer")) is Layer.TRAINERS
    assert layer_of(mark("vending_machine")) is Layer.NPCS
    with pytest.raises(ValueError, match="inconnu"):
        layer_of(mark("sign"))


def test_wild_preview_cycles_through_the_terrain_pokemon() -> None:
    points = frozenset({(8, 8), (24, 8), (40, 8)})
    assert wild_preview(points, [16, 19]) == [((8, 8), 16), ((24, 8), 19), ((40, 8), 16)]
    assert wild_preview(points, []) == []


def test_only_checked_layers_are_drawn_even_across_the_border(tmp_path: Path) -> None:
    base = Image.new("RGBA", (64, 64), (0, 0, 0, 255))
    painter = OverlayPainter(tmp_path)
    # Une entrée au bord : seule sa partie dans le lieu est dessinée.
    marks = [mark("warp", 0, 0), mark("vending_machine")]
    assert painter.paint(base, ROOM, marks, frozenset(), []).tobytes() == base.tobytes()
    warps = painter.paint(base, ROOM, marks, frozenset({Layer.WARPS}), [])
    assert warps.getpixel((1, 1)) != (0, 0, 0, 255)
    assert warps.getpixel((32, 32)) == (0, 0, 0, 255)
    facilities = painter.paint(base, ROOM, marks, frozenset({Layer.NPCS}), [])
    assert facilities.getpixel((32, 32)) != (0, 0, 0, 255)


def test_missing_asset_names_the_file(tmp_path: Path) -> None:
    base = Image.new("RGBA", (64, 64))
    with pytest.raises(FileNotFoundError, match="youngster"):
        OverlayPainter(tmp_path).paint(base, ROOM, [mark("npc", sprite="youngster")], frozenset(Layer), [])


def test_catalog_lists_objects_and_warps(database: Path) -> None:
    catalog = EditorCatalog(database)
    try:
        [family] = catalog.families()
        route = next(found for found in catalog.maps(family) if found.identifier == "route-2")
        kinds = {found.kind for found in catalog.marks(route)}
        assert {"warp", "item"} <= kinds
        assert all(found.item is not None for found in catalog.marks(route) if found.kind == "item")
    finally:
        catalog.close()


@pytest.mark.usefixtures("source_cache_ready")
def test_wild_terrains_follow_the_game() -> None:
    terrains = WildTerrains(CACHE)
    assert terrains.kinds(FAMILY, "route-1") == {"grass"}
    assert terrains.kinds(FAMILY, "viridian-forest") == {"grass"}
    assert terrains.kinds(FAMILY, "cerulean-cave-1f") == {"floor", "water"}
    assert terrains.kinds(FAMILY, "safari-zone-center") == {"grass", "water"}
    assert terrains.kinds(FAMILY, "absent") == frozenset()


def test_wild_terrains_require_the_pret_sources(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="build_data"):
        WildTerrains(tmp_path).kinds(FAMILY, "route-1")
