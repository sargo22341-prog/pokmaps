"""Cartes préparatoires de Rouge Feu/Vert Feuille, sans activer les jeux dans Room."""

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import EXTERNAL_EVENT_NOTE, FIRERED_LEAFGREEN
from pokemaps_data.maps import read_map_names
from pokemaps_data.maps_gen3 import export_gen3_maps, validate_catalog
from pokemaps_data.maps_layout import MapParent, read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.maps_render_gen3 import Gen3Renderer
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_animation import animation_tiles
from pokemaps_data.pret_gen3_sprites import sprite_image
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


def _rows(folder: Path) -> dict[str, dict[str, str]]:
    with (folder / "catalog.tsv").open(encoding="utf-8", newline="") as handle:
        return {row["const"]: row for row in csv.DictReader(handle, delimiter="\t")}


def test_remake_catalog_has_separate_regions_and_complete_plans(assets: Path) -> None:
    folder = assets / "maps/firered-leafgreen"
    validate_catalog(folder)
    rows = _rows(folder)
    assert len(rows) == 504
    assert {c for c, row in rows.items() if row["is_world"] == "True"} == {"KANTO", "SEVII"}
    assert not any("PROTOTYPE" in c or "UNUSED" in c for c in rows)
    assert rows["MAP_PALLET_TOWN"]["parent"] == "KANTO"
    assert rows["MAP_FOUR_ISLAND"]["parent"] == "SEVII"
    assert rows["MAP_SAFFRON_CITY_CONNECTION"]["parent"] == "KANTO"
    assert rows["MAP_SAFFRON_CITY"]["origin"] == "MAP_ROUTE5"
    for stem, floors in (("SILPH_CO", 11), ("POKEMON_TOWER", 7), ("VICTORY_ROAD", 3)):
        for floor in range(1, floors + 1):
            assert rows[f"MAP_{stem}_{floor}F"]["parent"] == f"{stem}_{floor}F_PLAN"
    assert rows["MAP_MT_EMBER_RUBY_PATH_B1F_STAIRS"]["parent"] == "MT_EMBER_RUBY_PATH_B1F_PLAN"
    assert rows["MAP_NAVEL_ROCK_FORK"]["parent"] == "NAVEL_ROCK_B2F_PLAN"
    chambers = [row for c, row in rows.items() if c.endswith("_CHAMBER")]
    assert len(chambers) == 7 and {row["parent"] for row in chambers} == {"TANOBY_RUINS_PLAN"}
    assert {row["name_fr"] for row in chambers} == {
        f"Ruines Tanoby (Chambre {name})"
        for name in ("Anémune", "Deulipe", "Prois", "Jonquatr", "Hibicinq", "Irix", "Poinsept")
    }


def test_remake_events_keep_invisible_journals_and_event_islands(assets: Path) -> None:
    folder = assets / "maps/firered-leafgreen"
    events = json.loads((folder / "events.json").read_text("utf-8"))
    journals = []
    for const, current in events.items():
        if const.startswith(("MAP_NAVEL_ROCK", "MAP_BIRTH_ISLAND")):
            assert EXTERNAL_EVENT_NOTE in current["notes"]
        for obj in current["objects"]:
            fields = dict(obj["fields"])
            sprite = str(fields["graphics_id"])
            if fields["movement_type"] == "MOVEMENT_TYPE_INVISIBLE":
                journals.append(fields)
            elif not sprite.startswith("OBJ_EVENT_GFX_VAR_"):
                assert (folder / "sprites" / f"{sprite.lower().replace('_', '-')}.webp").is_file()
    assert len(journals) == 19
    assert all(fields["script"] and fields["flag"] for fields in journals)
    assert not (folder / "sprites/0.webp").exists()
    with Image.open(folder / "sprites/obj-event-gfx-seagallop.webp") as ship:
        assert ship.size == (64, 64) and ship.getextrema()[3] == (0, 255)
    for path in folder.rglob("*.webp"):
        with Image.open(path) as image:
            assert image.format == "WEBP"
            if path.parent.name.isdecimal():
                assert image.size == (256, 256)


@pytest.fixture
def remake_maps(source_cache_ready: None) -> Gen3GameMaps:
    game = FIRERED_LEAFGREEN
    repo = Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    return Gen3GameMaps(repo, game, read_layout_curation())


def test_remake_sources_assemble_seven_islands_without_overlap(remake_maps: Gen3GameMaps, assets: Path) -> None:
    worlds = remake_maps.world_blocks
    # Les 38 cartes de Kanto incluent Safrania réelle, séparée de sa bordure de connexion.
    assert len(worlds["KANTO"]) == 37
    assert len(worlds["SEVII"]) == 24
    for name in ("ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN"):
        assert f"MAP_{name}_ISLAND" in worlds["SEVII"]
    assert len(remake_maps.maps) == len(remake_maps.placements) == 417
    rows = _rows(assets / "maps/firered-leafgreen")
    assert set(remake_maps.placements) <= rows.keys()
    assert read_map_names()[FIRERED_LEAFGREEN.map_family].keys() == remake_maps.maps.keys() | worlds.keys()
    assert set(remake_maps.parents.values()) <= remake_maps.world_region.keys()
    assert "MAP_PROTOTYPE_SEVII_ISLE_6" not in remake_maps.maps


def test_remake_curation_is_used_and_distinct_from_original_kanto(remake_maps: Gen3GameMaps) -> None:
    curation = read_layout_curation()
    family = FIRERED_LEAFGREEN.map_family
    for entries in (curation.anchors, curation.parents, curation.plans):
        assert {entry.map for entry in entries if entry.family == family} <= remake_maps.maps.keys()
    assert len(remake_maps.anchors) == 6
    assert len(remake_maps.plans) == 85
    assert all(part.family == family for part in remake_maps.plan_parts)
    assert len(remake_maps.plans["TANOBY_RUINS_PLAN"].parts) == 7
    assert len(remake_maps.plans["MT_EMBER_RUBY_PATH_B1F_PLAN"].parts) == 2


def test_remake_palettes_borders_animations_and_ship_frames(remake_maps: Gen3GameMaps) -> None:
    repo = remake_maps.repo
    renderer = Gen3Renderer(remake_maps, repo)
    current = remake_maps.maps["MAP_PALLET_TOWN"]
    blocks = renderer.blocks(current)
    layout = current.layout
    assert (layout.border_width, layout.border_height) == (2, 2)
    assert renderer.border(current, -1, -1).tobytes() == blocks[layout.border[-1] & 1023].tobytes()
    primary = repo.tilesets["gTileset_General"]
    assert primary.primary_tile_count == primary.primary_metatile_count == 640
    assert primary.primary_palette_count == 7
    assert len(animation_tiles(repo, primary)) == 70
    assert sprite_image(repo, "OBJ_EVENT_GFX_SEAGALLOP").size == (64, 64)
    assert sprite_image(repo, "OBJ_EVENT_GFX_SS_ANNE").size == (128, 64)


def test_remake_missing_french_name_stops_before_writing(
    remake_maps: Gen3GameMaps, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    names = read_map_names()[FIRERED_LEAFGREEN.map_family].copy()
    del names["MAP_PALLET_TOWN"]
    monkeypatch.setattr("pokemaps_data.maps_gen3.read_map_names", lambda: {FIRERED_LEAFGREEN.map_family: names})
    output = tmp_path / FIRERED_LEAFGREEN.version_group
    with pytest.raises(ValueError, match="MAP_PALLET_TOWN"):
        export_gen3_maps(CACHE, output, FIRERED_LEAFGREEN)
    assert not output.exists()


def test_remake_curation_rejects_unknown_maps(remake_maps: Gen3GameMaps) -> None:
    curation = read_layout_curation()
    unknown = MapParent(FIRERED_LEAFGREEN.map_family, "MAP_UNKNOWN", "MAP_PALLET_TOWN")
    invalid = replace(curation, parents=(*curation.parents, unknown))
    with pytest.raises(ValueError, match="MAP_UNKNOWN"):
        Gen3GameMaps(remake_maps.repo, FIRERED_LEAFGREEN, invalid)
