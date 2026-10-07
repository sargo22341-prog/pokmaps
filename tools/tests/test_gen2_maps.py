"""Cartes d'Or et d'Argent (phase 3 de plan_gen_2.md) : cartes du monde, rendu en couleurs et terrains."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import GOLD_SILVER
from pokemaps_data.maps import GameMapData
from pokemaps_data.maps_layout import (
    ConnectionSkip,
    GameMaps,
    LayoutCuration,
    MapAnchor,
    MapParent,
    read_layout_curation,
)
from pokemaps_data.maps_render_gen2 import Gen2Renderer
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.pret_source import macro_args, source_lines

FAMILY = GOLD_SILVER.map_family
# Palettes chargées dans un intérieur de jour : environment_colors.asm, .IndoorColors, ligne « day ».
INDOOR_DAY = (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x07)
PALETTE_NAMES = ("GRAY", "RED", "GREEN", "WATER", "YELLOW", "BROWN", "ROOF", "TEXT")


def test_one_world_map_per_region(gold_silver_maps: GameMaps) -> None:
    world = gold_silver_maps.world_blocks
    assert set(world) == {"JOHTO", "KANTO"}
    assert gold_silver_maps.world_size("JOHTO") == (235, 135)
    assert gold_silver_maps.world_size("KANTO") == (140, 135)
    assert {"NEW_BARK_TOWN", "ROUTE_26", "ROUTE_27", "SILVER_CAVE_OUTSIDE"} <= world["JOHTO"].keys()
    assert {"PALLET_TOWN", "ROUTE_22", "CINNABAR_ISLAND"} <= world["KANTO"].keys()
    # La Route 28 n'a aucune connexion vers la Route 26 : elle est ancrée à l'ouest de son extrémité nord.
    x, y = world["JOHTO"]["ROUTE_26"]
    assert world["JOHTO"]["ROUTE_28"] == (x - 20, y)


def test_detached_outdoor_maps_are_reached_by_warps(gold_silver_maps: GameMaps) -> None:
    parents = gold_silver_maps.parents
    detached = {const for const in parents if gold_silver_maps.maps[const].is_outdoor}
    assert detached == {
        "MOUNT_MOON_SQUARE",
        "NATIONAL_PARK",
        "NATIONAL_PARK_BUG_CONTEST",
        "OLIVINE_PORT",
        "ROUTE_23",
        "RUINS_OF_ALPH_OUTSIDE",
        "TIN_TOWER_ROOF",
        "VERMILION_PORT",
    }
    # On n'entre dans le Parc Naturel du Concours que par le script d'inscription (commande warp).
    assert parents["NATIONAL_PARK_BUG_CONTEST"] == "ROUTE_35"
    assert parents["RUINS_OF_ALPH_OUTSIDE"] == "ROUTE_32"
    # Cartes de test que seuls des warps « inaccessible » atteignent : jamais affichées.
    assert not {"OLIVINE_HOUSE_BETA", "SAFARI_ZONE_BETA"} & gold_silver_maps.placements.keys()
    assert len(gold_silver_maps.placements) == 355


def test_victory_road_is_entered_from_route_26(gold_silver_maps: GameMaps) -> None:
    # La porte s'ouvre aussi sur la Route 28 (n° de carte plus petit), atteinte seulement après la Ligue.
    parents = gold_silver_maps.parents
    reached = ("VICTORY_ROAD_GATE", "VICTORY_ROAD", "ROUTE_23", "INDIGO_PLATEAU_POKECENTER_1F")
    assert {const: parents[const] for const in reached} == dict.fromkeys(reached, "ROUTE_26")
    assert parents["ROUTE_28_STEEL_WING_HOUSE"] == "ROUTE_28"


def test_layout_curation_is_checked(gold_silver_repo: Gen2PretRepo) -> None:
    curation = read_layout_curation()

    def layout(
        anchors: tuple[MapAnchor, ...], skips: tuple[ConnectionSkip, ...], parents: tuple[MapParent, ...] = ()
    ) -> GameMaps:
        return GameMaps(gold_silver_repo, GOLD_SILVER, LayoutCuration(anchors, skips, parents))

    with pytest.raises(ValueError, match="Connexion incohérente CELADON_CITY"):
        _ = layout(curation.anchors, ()).world_blocks
    with pytest.raises(ValueError, match="déjà relié par une connexion"):
        _ = layout(
            (*curation.anchors, MapAnchor(FAMILY, "ROUTE_29", "NEW_BARK_TOWN", -30, 0)), curation.skips
        ).world_blocks
    with pytest.raises(ValueError, match="connexion inconnue"):
        layout(curation.anchors, (*curation.skips, ConnectionSkip(FAMILY, "ROUTE_29", "PALLET_TOWN")))
    with pytest.raises(ValueError, match="reliées à aucune carte du monde"):
        _ = layout((), curation.skips).parents
    with pytest.raises(ValueError, match="aucun warp de ROUTE_29 vers VICTORY_ROAD_GATE"):
        _ = layout(curation.anchors, curation.skips, (MapParent(FAMILY, "VICTORY_ROAD_GATE", "ROUTE_29"),)).parents
    with pytest.raises(ValueError, match="ne mène pas d'une carte du monde"):
        _ = layout(curation.anchors, curation.skips, (MapParent(FAMILY, "VICTORY_ROAD", "VICTORY_ROAD_GATE"),)).parents


def _reference_interior(repo: Gen2PretRepo, const: str) -> Image.Image:
    """Image d'un intérieur de jour, recalculée sans le module de rendu : métatuile -> tuiles -> palette de chaque
    tuile (palette_map) -> couleurs de bg_tiles.pal."""
    pret_map = repo.maps[const]
    tileset = repo.tilesets[pret_map.tileset]
    lines = source_lines(repo.path("gfx/tilesets/bg_tiles.pal"))
    values = [[int(v) for v in macro_args(line, "RGB")] for line in lines if line.startswith("RGB ")]
    colors = [[tuple((c << 3) | (c >> 2) for c in row[i : i + 3]) for i in range(0, 12, 3)] for row in values]
    palettes = {name: colors[index] for name, index in zip(PALETTE_NAMES, INDOOR_DAY, strict=True)}
    gfx = Image.open(tileset.gfx).convert("L")
    image = Image.new("RGB", (pret_map.width * 32, pret_map.height * 32))
    for by in range(pret_map.height):
        for bx in range(pret_map.width):
            metatile = tileset.metatiles[pret_map.block(bx, by) * 16 :][:16]
            for position, tile in enumerate(metatile):
                palette = palettes[tileset.palettes[tile]]
                for y in range(8):
                    for x in range(8):
                        shade = 3 - round(gfx.getpixel(((tile % 16) * 8 + x, (tile // 16) * 8 + y)) / 85)
                        target = (bx * 32 + (position % 4) * 8 + x, by * 32 + (position // 4) * 8 + y)
                        image.putpixel(target, palette[shade])
    return image


def test_interior_rendering_matches_a_computed_reference(gold_silver_maps: GameMaps) -> None:
    rendered = Gen2Renderer(gold_silver_maps, gold_silver_maps.repo).render("ELMS_LAB")
    assert (rendered.width, rendered.height, rendered.level_count) == (160, 192, 1)
    assert rendered.image.tobytes() == _reference_interior(gold_silver_maps.repo, "ELMS_LAB").tobytes()


def test_day_palettes_roofs_and_flash(gold_silver_maps: GameMaps) -> None:
    repo = gold_silver_maps.repo
    renderer = Gen2Renderer(gold_silver_maps, repo)
    roof_lines = [line for line in source_lines(repo.path("gfx/tilesets/roofs.pal")) if line.startswith("RGB ")]
    new_bark = repo.headers["NEW_BARK_TOWN"]
    light, dark = (
        [int(v) for v in macro_args(line, "RGB")] for line in roof_lines[new_bark.group * 4 : new_bark.group * 4 + 2]
    )
    roof = renderer.palettes(new_bark)[PALETTE_NAMES.index("ROOF")]
    assert roof[1:3] == tuple(tuple((c << 3) | (c >> 2) for c in color) for color in (light, dark))
    # Grotte sombre : rendue avec les couleurs de nuit, celles qu'elle prend après Flash.
    dark_cave = repo.headers["DARK_CAVE_VIOLET_ENTRANCE"]
    union_cave = repo.headers["UNION_CAVE_1F"]
    assert (dark_cave.palette, union_cave.palette) == ("PALETTE_DARK", "PALETTE_NITE")
    assert renderer.palettes(dark_cave) == renderer.palettes(union_cave)


def test_wild_terrains_follow_the_collisions(gold_silver_maps: GameMaps) -> None:
    def terrains(const: str) -> dict[str, int]:
        return {kind: len(cells) for kind, cells in gold_silver_maps.cells(const).items()}

    assert terrains("ROUTE_29") == {"grass": 160, "water": 0, "floor": 0}
    # En grotte et en donjon, chaque pas déclenche une rencontre ; dehors, seulement les herbes et l'eau.
    assert terrains("UNION_CAVE_1F")["floor"] > 0
    assert terrains("NEW_BARK_TOWN")["floor"] == 0
    # Le Lac Colère n'a pas de hautes herbes dans Or et Argent (PokéAPI n'y donne pas de rencontre en marchant).
    assert terrains("LAKE_OF_RAGE") == {"grass": 0, "water": 300, "floor": 0}
    # Pas de rencontre sur la glace de la Route de Glace.
    repo = gold_silver_maps.repo
    ice_path = repo.maps["ICE_PATH_1F"]
    tileset = repo.tilesets[ice_path.tileset]
    floor = set(gold_silver_maps.cells("ICE_PATH_1F")["floor"])
    ice = {
        (x, y)
        for y in range(ice_path.height * 2)
        for x in range(ice_path.width * 2)
        if tileset.collisions[ice_path.block(x // 2, y // 2)][(y % 2) * 2 + x % 2] in repo.collisions.ice
    }
    assert ice
    assert not ice & floor


def test_exported_maps(gold_silver_export: tuple[GameMapData, Path]) -> None:
    data, output = gold_silver_export
    displayed = {row.const: row for row in data.maps if row.parent is None}
    assert (displayed["JOHTO"].number, displayed["JOHTO"].name_fr) == (998, "Johto")
    assert (displayed["KANTO"].number, displayed["KANTO"].name_fr) == (999, "Kanto")
    assert (displayed["JOHTO"].width, displayed["JOHTO"].height, displayed["JOHTO"].level_count) == (7520, 4320, 6)
    children = {row.const: row.parent for row in data.maps if row.parent}
    assert children["NEW_BARK_TOWN"] == "JOHTO"
    assert children["PALLET_TOWN"] == "KANTO"
    assert len({row.number for row in data.maps}) == len(data.maps)
    assert (output / "johto/0/0_0.webp").is_file()
    assert any((output / "johto/5").glob("*.webp"))
    assert (output / "sprites/youngster.webp").is_file()
    legendaries = {(row.pokemon, row.level, row.version) for row in data.objects if row.kind == "pokemon"}
    assert {("ho-oh", 40, "gold"), ("ho-oh", 70, "silver"), ("snorlax", 50, None)} <= legendaries
    joey = next(row for row in data.objects if row.text == "TrainerYoungsterJoey")
    assert (joey.trainer_class, joey.party) == ("youngster", [("rattata", 4, ("tackle", "tail-whip"))])
    # Le warp -1 de l'ascenseur arrive au warp du Centre commercial qui y mène.
    elevator = [row for row in data.warps if row.map_const == "CELADON_DEPT_STORE_ELEVATOR"]
    assert {row.target for row in elevator} == {"CELADON_DEPT_STORE_1F"}
    assert all(row.target_x is not None for row in elevator)
