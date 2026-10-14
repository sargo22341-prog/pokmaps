"""Passages GBA sans warp, cartes et dessins propres à une version, mer répétée des Îles Sevii."""

import csv
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from pokemaps_data.games import EMERALD, FIRERED_LEAFGREEN, RUBY_SAPPHIRE, Game
from pokemaps_data.maps_gen3 import SEA_TILES, version_patch_folder
from pokemaps_data.maps_layout import read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


def _rows(folder: Path, name: str) -> list[dict[str, str]]:
    with (folder / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


@pytest.mark.parametrize("game", [EMERALD, RUBY_SAPPHIRE], ids=lambda game: game.version_group)
def test_hoenn_passages_without_warp(assets: Path, game: Game) -> None:
    folder = assets / "maps" / game.version_group
    maps = {row["const"]: row for row in _rows(folder, "catalog.tsv")}
    warps = _rows(folder, "warps.tsv")
    kinds = {kind: [row for row in warps if row["kind"] == kind] for kind in ("dive", "cable_car", "secret_base")}
    # Le téléphérique relie dans les deux sens la station de la Route 112 et celle du Mont Chimnée.
    stations = {(row["map_const"], row["target"]) for row in kinds["cable_car"]}
    assert stations == {
        ("MAP_ROUTE112_CABLE_CAR_STATION", "MAP_MT_CHIMNEY_CABLE_CAR_STATION"),
        ("MAP_MT_CHIMNEY_CABLE_CAR_STATION", "MAP_ROUTE112_CABLE_CAR_STATION"),
    }
    # Chaque plongée scriptée a son retour, dont l'entrée du Sanctuaire des Regi depuis le fond du Chenal 134.
    dives = {(row["map_const"], row["target"]) for row in kinds["dive"]}
    assert {(target, source) for source, target in dives} == dives
    assert ("MAP_ROUTE134", "MAP_UNDERWATER_ROUTE134") in dives
    assert ("MAP_UNDERWATER_SEALED_CHAMBER", "MAP_SEALED_CHAMBER_OUTER_ROOM") in dives
    assert len(kinds["dive"]) == (14 if game == EMERALD else 12)
    # 75 entrées de Bases Secrètes, sur des villes et routes de Hoenn, vers une carte modèle.
    assert len(kinds["secret_base"]) == 75
    for row in kinds["secret_base"]:
        assert maps[row["map_const"]]["parent"] == "HOENN"
        assert row["target"].startswith("MAP_SECRET_BASE_")
    assert len({(row["map_const"], row["x"], row["y"]) for row in kinds["secret_base"]}) == 75


def test_hideouts_belong_to_their_version(assets: Path) -> None:
    rows = _rows(assets / "maps/ruby-sapphire", "catalog.tsv")
    versions = {row["const"]: row["version"] for row in rows}
    assert {const for const in versions if "MAGMA_HIDEOUT" in const}
    assert all(versions[const] == "ruby" for const in versions if "MAGMA_HIDEOUT" in const)
    assert all(versions[const] == "sapphire" for const in versions if "AQUA_HIDEOUT" in const)
    assert {version for const, version in versions.items() if "HIDEOUT" not in const} == {""}
    for group in ("emerald", "firered-leafgreen"):
        assert {row["version"] for row in _rows(assets / "maps" / group, "catalog.tsv")} == {""}


def test_ruby_redraws_the_lilycove_hideout_entrance(assets: Path) -> None:
    world = next(row for row in _rows(assets / "maps/ruby-sapphire", "catalog.tsv") if row["const"] == "HOENN")
    folder = assets / "maps/ruby-sapphire" / version_patch_folder("HOENN", "ruby")
    assert folder.name == "hoenn-ruby"
    # Une seule zone retouchée : une tuile par niveau, sauf si elle chevauche une limite de tuile.
    levels = sorted(int(path.name) for path in folder.iterdir())
    assert levels == list(range(int(world["level_count"])))
    for path in folder.rglob("*.webp"):
        with Image.open(path) as tile:
            assert tile.size == (256, 256) and tile.mode == "RGBA"
            # Aux niveaux réduits, les douze cases tiennent dans quelques pixels mêlés à la transparence.
            low, high = tile.getextrema()[3]
            assert low == 0 and (high == 255 if path.parent.name == str(levels[-1]) else high > 0)
    for group in ("emerald", "firered-leafgreen"):
        assert not any(path.name.endswith(("-ruby", "-sapphire")) for path in (assets / "maps" / group).iterdir())
    assert not (assets / "maps/ruby-sapphire/hoenn-sapphire").exists()


def test_sevii_sea_is_one_opaque_tile_per_zoom_level(assets: Path) -> None:
    folder = assets / "maps/firered-leafgreen"
    sevii = next(row for row in _rows(folder, "catalog.tsv") if row["const"] == "SEVII")
    tiles = sorted((folder / SEA_TILES).iterdir(), key=lambda path: int(path.stem))
    assert [path.name for path in tiles] == [f"{level}.webp" for level in range(int(sevii["level_count"]))]
    for path in tiles:
        with Image.open(path) as tile:
            assert tile.size == (256, 256)
            assert tile.mode == "RGB"
    for group in ("emerald", "ruby-sapphire"):
        assert not (assets / "maps" / group / SEA_TILES).exists()


def test_a_bed_is_a_single_heal_spot(db: sqlite3.Connection) -> None:
    neighbours = db.execute(
        """
        SELECT m.identifier FROM map_object a
        JOIN map_object b ON b.map_id = a.map_id AND b.id > a.id
            AND COALESCE(b.version_id, 0) = COALESCE(a.version_id, 0)
        JOIN map m ON m.id = a.map_id
        WHERE a.kind = 'heal_spot' AND b.kind = 'heal_spot' AND ABS(a.x - b.x) <= 16 AND ABS(a.y - b.y) <= 16
        """
    ).fetchall()
    assert neighbours == []
    institute = db.execute(
        """
        SELECT COUNT(*) FROM map_object o JOIN map m ON m.id = o.map_id
        WHERE o.kind = 'heal_spot' AND m.identifier = 'route119-weather-institute-1f'
        """
    ).fetchone()
    assert institute == (3,)  # Rubis, Saphir et Émeraude


@pytest.mark.pipeline
def test_version_patches_follow_the_on_load_scripts(source_cache_ready: None) -> None:
    curation = read_layout_curation()
    repo = Gen3PretRepo(pret_dir(CACHE, RUBY_SAPPHIRE.pret_repo), RUBY_SAPPHIRE.pret_versions)
    game_maps = Gen3GameMaps(repo, RUBY_SAPPHIRE, curation)
    patches = game_maps.version_patches
    assert set(patches) == {"ruby"} and set(patches["ruby"]) == {"MAP_LILYCOVE_CITY"}
    cells = patches["ruby"]["MAP_LILYCOVE_CITY"]
    assert set(cells) == {(x, y) for x in range(69, 73) for y in range(4, 7)}
    # La case du passage vers la Planque Magma est l'ouverture que Rubis dessine.
    lilycove = game_maps.maps["MAP_LILYCOVE_CITY"]
    magma = next(warp for warp in lilycove.warps if warp.target == "MAP_MAGMA_HIDEOUT_1F")
    assert (magma.x, magma.y) == (71, 5)
    assert game_maps.version_maps["MAP_MAGMA_HIDEOUT_1F"] == "ruby"
    assert game_maps.version_maps["MAP_AQUA_HIDEOUT_1F"] == "sapphire"
    for game in (EMERALD, FIRERED_LEAFGREEN):
        other = Gen3GameMaps(Gen3PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions), game, curation)
        assert other.version_patches == {}
        assert other.version_maps == {}
