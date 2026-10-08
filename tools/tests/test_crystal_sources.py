"""Différences de format de Cristal, vérifiées sur le désassemblage épinglé."""

from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import CRYSTAL
from pokemaps_data.maps_layout import GameMaps, read_layout_curation
from pokemaps_data.maps_render_gen2 import Gen2Renderer
from pokemaps_data.pret_gen2 import Gen2PretRepo
from pokemaps_data.pret_gen2_scripts import ScriptFile
from pokemaps_data.pret_gen2_wild import wild_tables
from pokemaps_data.pret_models import NpcOffer


def test_crystal_maps_and_script_warps(crystal_repo: Gen2PretRepo) -> None:
    assert len(crystal_repo.maps) == 388
    maps = GameMaps(crystal_repo, CRYSTAL, read_layout_curation())
    assert maps.parents["NATIONAL_PARK_BUG_CONTEST"] == "ROUTE_35"
    assert maps.parents["BATTLE_TOWER_BATTLE_ROOM"] == "ROUTE_40"
    assert maps.parents["DRAGON_SHRINE"] == "BLACKTHORN_CITY"
    assert maps.world_size("JOHTO") == (235, 135)
    assert maps.world_size("KANTO") == (140, 135)


def test_second_tile_bank_uses_its_image_and_palette(crystal_repo: Gen2PretRepo) -> None:
    maps = GameMaps(crystal_repo, CRYSTAL, read_layout_curation())
    renderer = Gen2Renderer(maps, crystal_repo)
    tileset = crystal_repo.tilesets["TILESET_JOHTO_MODERN"]
    assert tileset.metatiles[102 * 16] == 212
    assert tileset.palettes[212] == "RED"
    assert tileset.palettes[96:128] == (None,) * 32
    block = renderer.blocks(crystal_repo.maps["GOLDENROD_CITY"])[102]
    palette = renderer.palettes(crystal_repo.headers["GOLDENROD_CITY"])[1]
    with Image.open(tileset.gfx) as source:
        gray = source.convert("L")
        # $d4 dans la seconde banque correspond à la tuile 180 de l'image, après les 96 premières.
        expected = [palette[3 - round(gray.getpixel((32 + x, 88 + y)) / 85)] for y in range(8) for x in range(8)]
    assert [block.getpixel((x, y)) for y in range(8) for x in range(8)] == expected


def test_suicune_is_a_scene_battle(crystal_repo: Gen2PretRepo) -> None:
    suicune = [obj for obj in crystal_repo.maps["TIN_TOWER_1F"].objects if obj.pokemon == "SUICUNE"]
    assert len(suicune) == 1
    assert (suicune[0].kind, suicune[0].level) == ("pokemon", 40)


def test_crystal_wild_tables_are_not_empty(crystal_repo: Gen2PretRepo) -> None:
    tables = wild_tables(crystal_repo, "_CRYSTAL")
    assert len(tables) == 615
    assert all(sum(slot.chance for slot in table.slots) == 100 for table in tables)
    methods = {table.method for table in tables}
    assert methods == {"walk", "surf", "old-rod", "good-rod", "super-rod", "headbutt", "headbutt-high", "rock-smash"}
    assert any(table.map_const == "DARK_CAVE_VIOLET_ENTRANCE" and "swarm-yes" in table.conditions for table in tables)


def test_odd_eggs_and_tutor_are_read(crystal_repo: Gen2PretRepo) -> None:
    reader = crystal_repo.offers
    eggs = reader.script_offers(crystal_repo.script_files["DayCare"], "DayCareManScript_Inside").offers
    assert {offer.pokemon for offer in eggs if offer.kind == "gift_egg"} == {
        "PICHU",
        "CLEFFA",
        "IGGLYBUFF",
        "TYROGUE",
        "SMOOCHUM",
        "ELEKID",
        "MAGBY",
    }
    tutor = reader.script_offers(crystal_repo.script_files["GoldenrodCity"], "MoveTutorScript").offers
    assert tutor == (NpcOffer("move_tutor", price=4000),)


def test_international_script_branch_and_unknown_condition(tmp_path: Path) -> None:
    path = tmp_path / "script.asm"
    path.write_text("Script:\nif DEF(_CRYSTAL_AU)\ngiveitem POTION\nelse\ngiveitem REPEL\nendc\nend\n", "utf-8")
    assert ScriptFile(path).reachable_lines("Script", None) == ["giveitem REPEL", "end"]
    assert ScriptFile(path, frozenset({"_CRYSTAL_AU"})).reachable_lines("Script", None) == ["giveitem POTION", "end"]
    path.write_text("Script:\nif UNKNOWN\nend\nendc\n", "utf-8")
    with pytest.raises(ValueError, match="condition non prise en charge"):
        _ = ScriptFile(path).blocks
