"""Catalogues Hoenn versionnés et comparaison avec les sources épinglées."""

import csv
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import EMERALD, RUBY_SAPPHIRE, Game
from pokemaps_data.maps import read_map_names
from pokemaps_data.maps_gen3 import HOENN_MAP_GAMES, validate_catalog
from pokemaps_data.maps_layout import identifier, read_layout_curation
from pokemaps_data.maps_layout_gen3 import UNDERWATER, Gen3GameMaps
from pokemaps_data.maps_render_gen3 import Gen3Renderer
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_animation import animation_tiles
from pokemaps_data.pret_gen3_sprites import sprite_image
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


def _catalog(folder: Path) -> dict[str, dict[str, str]]:
    with (folder / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        return {row["const"]: row for row in csv.DictReader(handle, delimiter="\t")}


@pytest.mark.parametrize("game", HOENN_MAP_GAMES, ids=lambda game: game.version_group)
def test_bundled_hoenn_catalog_and_images(assets: Path, game: Game) -> None:
    folder = assets / "maps" / game.version_group
    validate_catalog(folder)
    maps = _catalog(folder)
    # Les plans GBA regroupent les salles d'un même étage, comme en 1re et 2e génération.
    assert len(maps) == (582 if game == EMERALD else 433)
    assert {key for key, row in maps.items() if row["is_world"] == "True"} == {"HOENN", UNDERWATER}
    assert not any("UNUSED" in key or "PROTOTYPE" in key for key in maps)
    assert maps["MAP_ROUTE130_MIRAGE_ISLAND"]["origin"] == "MAP_ROUTE130"
    assert maps["MAP_SOOTOPOLIS_CITY"]["origin"].startswith("MAP_UNDERWATER")
    assert maps["MAP_SHOAL_CAVE_HIGH_TIDE_ENTRANCE_ROOM"]["parent"] == "SHOAL_CAVE_HIGH_TIDE_1F_PLAN"
    assert maps["MAP_SHOAL_CAVE_LOW_TIDE_ENTRANCE_ROOM"]["parent"] == "SHOAL_CAVE_LOW_TIDE_1F_PLAN"
    for room, plan in (
        ("MAP_METEOR_FALLS_1F_1R", "METEOR_FALLS_1F_PLAN"),
        ("MAP_METEOR_FALLS_1F_2R", "METEOR_FALLS_1F_PLAN"),
        ("MAP_METEOR_FALLS_B1F_1R", "METEOR_FALLS_B1F_PLAN"),
        ("MAP_METEOR_FALLS_B1F_2R", "METEOR_FALLS_B1F_PLAN"),
        ("MAP_UNDERWATER_ROUTE134", "UNDERWATER_ROUTE134_PLAN"),
        ("MAP_UNDERWATER_SEALED_CHAMBER", "UNDERWATER_ROUTE134_PLAN"),
        ("MAP_NEW_MAUVILLE_ENTRANCE", "NEW_MAUVILLE_PLAN"),
        ("MAP_NEW_MAUVILLE_INSIDE", "NEW_MAUVILLE_PLAN"),
    ):
        assert maps[room]["parent"] == plan
    for path in folder.rglob("*.webp"):
        with Image.open(path) as image:
            assert image.format == "WEBP"
            assert image.size == ((256, 256) if path.parent.name.isdecimal() else image.size)
    events = json.loads((folder / "events.json").read_text("utf-8"))
    for current in events.values():
        for obj in current["objects"]:
            sprite = dict(obj["fields"])["graphics_id"]
            if not sprite.startswith("OBJ_EVENT_GFX_VAR_"):
                assert (folder / "sprites" / f"{sprite.lower().replace('_', '-')}.webp").is_file()


def test_catalog_rejects_a_missing_parent(assets: Path, tmp_path: Path) -> None:
    source = assets / "maps/emerald"
    target = tmp_path / "emerald"
    shutil.copytree(source, target)
    path = target / "catalog.tsv"
    text = path.read_text("utf-8").replace("\tHOENN\t", "\tUNKNOWN_WORLD\t", 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="parent invalide"):
        validate_catalog(target)


def test_catalog_rejects_a_missing_mirage_access(assets: Path, tmp_path: Path) -> None:
    target = tmp_path / "ruby-sapphire"
    shutil.copytree(assets / "maps/ruby-sapphire", target)
    path = target / "warps.tsv"
    lines = path.read_text("utf-8").splitlines()
    path.write_text(
        "\n".join(line for line in lines if "MAP_ROUTE130_MIRAGE_ISLAND" not in line) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Île Mirage : accès aller-retour"):
        validate_catalog(target)


@pytest.mark.pipeline
@pytest.mark.parametrize("game", HOENN_MAP_GAMES, ids=lambda game: game.version_group)
def test_hoenn_sources_place_regions_warps_and_tides(game: Game, source_cache_ready: None, assets: Path) -> None:
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    placed = Gen3GameMaps(repo, game, read_layout_curation())
    surface = placed.world_blocks["HOENN"]
    assert len(surface) == (57 if game == EMERALD else 54)
    assert len(placed.world_blocks[UNDERWATER]) == (7 if game == EMERALD else 4)
    for const, point in surface.items():
        for connection in repo.maps[const].connections:
            if connection.direction == "dive":
                assert placed.world_blocks[UNDERWATER][connection.target] == point
    assert len(placed.placements) == len(placed.maps)
    catalog = _catalog(assets / "maps" / game.version_group)
    assert set(placed.placements) <= catalog.keys()
    assert all(current.layout.const in repo.layouts for current in placed.maps.values())
    high = placed.maps["MAP_SHOAL_CAVE_HIGH_TIDE_ENTRANCE_ROOM"]
    assert high.warps and any(warp.accessible for warp in high.warps)
    assert all(warp.target == "MAP_ROUTE125" or "HIGH_TIDE" in warp.target for warp in high.warps)
    assert not placed.maps["MAP_SHOAL_CAVE_HIGH_TIDE_INNER_ROOM"].warps[1].accessible
    names = read_map_names()[game.map_family]
    assert set(placed.maps) <= names.keys()
    renderer = Gen3Renderer(placed, repo)
    first = next(iter(surface))
    current = placed.maps[first]
    blocks = renderer.blocks(current)
    assert renderer.border(current, 0, 0).tobytes() == blocks[current.layout.border[0] & 1023].tobytes()
    assert renderer.border(current, -1, -1).tobytes() == blocks[current.layout.border[-1] & 1023].tobytes()
    sprite = sprite_image(repo, "OBJ_EVENT_GFX_NURSE")
    assert sprite.size == (16, 32) and sprite.getextrema()[3] == (0, 255)
    primary = repo.tilesets["gTileset_General"]
    assert len(animation_tiles(repo, primary)) == 60
    assert identifier(high.const) == "shoal-cave-high-tide-entrance-room"


@pytest.mark.pipeline
def test_hoenn_curation_entries_are_used_by_a_family_member(source_cache_ready: None) -> None:
    curation = read_layout_curation()
    games = [
        Gen3GameMaps(Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions), game, curation)
        for game in (EMERALD, RUBY_SAPPHIRE)
    ]
    maps = set().union(*(game.maps for game in games))
    family = EMERALD.map_family
    assert {part.map for part in curation.plans if part.family == family} <= maps
    assert {entry.map for entry in curation.parents if entry.family == family} <= maps
    assert {entry.map for entry in curation.anchors if entry.family == family} <= maps
    assert {entry.map for entry in curation.skips if entry.family == family} <= maps
    assert maps | {"HOENN", UNDERWATER} == read_map_names()[family].keys()


@pytest.mark.parametrize("game", HOENN_MAP_GAMES, ids=lambda game: game.version_group)
def test_mirage_island_has_a_round_trip_navigation_access(assets: Path, game: Game) -> None:
    folder = assets / "maps" / game.version_group
    maps = _catalog(folder)
    # L'île a la taille de la carte du monde : elle se dessine en place, par-dessus le Chenal 130.
    island, world = maps["MAP_ROUTE130_MIRAGE_ISLAND"], maps["HOENN"]
    assert (island["width"], island["height"], island["level_count"]) == (
        world["width"],
        world["height"],
        world["level_count"],
    )
    with (folder / "warps.tsv").open(encoding="utf-8", newline="") as handle:
        warps = list(csv.DictReader(handle, delimiter="\t"))
    outward = [row for row in warps if row["target"] == "MAP_ROUTE130_MIRAGE_ISLAND"]
    returning = [row for row in warps if row["map_const"] == "MAP_ROUTE130_MIRAGE_ISLAND"]
    assert len(outward) == len(returning) == 1
    assert outward[0]["map_const"] == returning[0]["target"] == "MAP_ROUTE130"
    for row in [outward[0], returning[0]]:
        assert row["kind"] == "mirage"
        assert (row["x"], row["y"]) == (row["target_x"], row["target_y"])
        route = maps["MAP_ROUTE130"]
        assert int(route["x"]) <= int(row["x"]) < int(route["x"]) + int(route["width"])
        assert int(route["y"]) <= int(row["y"]) < int(route["y"]) + int(route["height"])
    # Le retour est posé dans l'eau sous la plage, pas sur l'île.
    assert outward[0]["x"] == returning[0]["x"]
    assert int(returning[0]["y"]) > int(outward[0]["y"])


def test_catalog_rejects_a_mirage_return_on_the_island(assets: Path, tmp_path: Path) -> None:
    target = tmp_path / "emerald"
    shutil.copytree(assets / "maps/emerald", target)
    path = target / "warps.tsv"
    rows = path.read_text("utf-8").splitlines()
    entrance = next(line for line in rows if line.startswith("MAP_ROUTE130\t") and line.endswith("\tmirage"))
    x, y = entrance.split("\t")[1:3]
    rows = [
        f"MAP_ROUTE130_MIRAGE_ISLAND\t{x}\t{y}\tMAP_ROUTE130\t{x}\t{y}\tmirage"
        if line.startswith("MAP_ROUTE130_MIRAGE_ISLAND\t")
        else line
        for line in rows
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="retour placé sur l'île"):
        validate_catalog(target)
