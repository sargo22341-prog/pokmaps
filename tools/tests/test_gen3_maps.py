"""Lecture des variantes de cartes GBA sur extraits réduits et sources épinglées."""

import json
import struct
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_maps import Gen3Map, read_layouts, read_maps
from pokemaps_data.pret_reader import open_pret
from pokemaps_data.sources import pret_dir


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def map_repo(tmp_path: Path) -> Path:
    layout = dict(
        id="LAYOUT_TEST",
        name="Test_Layout",
        width=2,
        height=2,
        primary_tileset="gTileset_General",
        secondary_tileset="gTileset_Test",
        border_filepath="data/layouts/Test/border.bin",
        blockdata_filepath="data/layouts/Test/map.bin",
    )
    _json(tmp_path / "data/layouts/layouts.json", {"layouts": [layout]})
    binary = tmp_path / "data/layouts/Test"
    binary.mkdir()
    (binary / "map.bin").write_bytes(struct.pack("<4H", 0xC401, 2, 3, 4))
    (binary / "border.bin").write_bytes(struct.pack("<4H", 5, 6, 7, 8))
    _json(tmp_path / "data/maps/map_groups.json", {"group_order": ["gGroup"], "gGroup": ["Test", "Shared"]})
    row = dict(
        id="MAP_TEST",
        name="Test",
        layout="LAYOUT_TEST",
        music="MUS_TEST",
        region_map_section="MAPSEC_TEST",
        requires_flash=False,
        weather="WEATHER_SUNNY",
        map_type="MAP_TYPE_ROUTE",
        show_map_name=True,
        battle_scene="MAP_BATTLE_SCENE_NORMAL",
        connections=[dict(map="MAP_SHARED", direction="dive", offset=0)],
        warp_events=[dict(x=1, y=1, elevation=3, dest_map="MAP_SHARED", dest_warp_id="0")],
        coord_events=[dict(type="trigger", x=1, y=0, elevation=3, var="VAR_TEST", var_value="1", script="Script")],
        bg_events=[
            dict(
                type="hidden_item",
                x=0,
                y=0,
                elevation=3,
                item="ITEM_POTION",
                flag="FLAG_ITEM",
                quantity=2,
                underfoot=True,
            )
        ],
        object_events=[],
    )
    _json(tmp_path / "data/maps/Test/map.json", row)
    shared = {
        key: value
        for key, value in row.items()
        if key not in {"object_events", "warp_events", "coord_events", "bg_events", "connections"}
    }
    shared.update(id="MAP_SHARED", name="Shared", shared_events_map="Test", shared_scripts_map="Test")
    _json(tmp_path / "data/maps/Shared/map.json", shared)
    return tmp_path


def _maps(root: Path) -> dict[str, Gen3Map]:
    return read_maps(root, read_layouts(root))


def test_layout_words_and_shared_events(map_repo: Path) -> None:
    maps = _maps(map_repo)
    surface, shared = maps["MAP_TEST"], maps["MAP_SHARED"]
    assert surface.layout.cells[0] == 0xC401
    assert surface.layout.block(0, 0) == 1
    assert surface.layout.border == (5, 6, 7, 8)
    assert surface.connections[0].direction == "dive"
    assert surface.warps[0].target_warp == 1
    assert surface.warps[0].elevation == 3
    assert shared.warps == surface.warps
    assert shared.coord_events[0].value("var_value") == "1"
    assert shared.bg_events[0].value("flag") == "FLAG_ITEM"
    assert shared.bg_events[0].value("quantity") == 2
    assert shared.bg_events[0].value("underfoot") is True
    assert shared.shared_scripts_map == "Test"
    with pytest.raises(ValueError, match="hors du layout"):
        surface.layout.block(2, 0)


def test_clone_objects_are_excluded(map_repo: Path) -> None:
    path = map_repo / "data/maps/Test/map.json"
    row = json.loads(path.read_text("utf-8"))
    row["object_events"] = [
        dict(type="clone", x=1, y=1, graphics_id="OBJ_EVENT_GFX_TEST", target_local_id="1", target_map="MAP_SHARED")
    ]
    _json(path, row)
    assert _maps(map_repo)["MAP_TEST"].objects == ()


@pytest.mark.parametrize("change", ["unknown_field", "unknown_event", "missing_target", "bad_coordinate"])
def test_invalid_map_data_fails(map_repo: Path, change: str) -> None:
    path = map_repo / "data/maps/Test/map.json"
    row = json.loads(path.read_text("utf-8"))
    if change == "unknown_field":
        row["new_engine_field"] = True
    elif change == "unknown_event":
        row["bg_events"][0]["type"] = "unknown"
    elif change == "missing_target":
        row["connections"][0]["map"] = "MAP_MISSING"
    elif change == "bad_coordinate":
        row["coord_events"][0]["x"] = "one"
    _json(path, row)
    with pytest.raises(ValueError, match=r"Test|MAP_TEST"):
        _maps(map_repo)


def test_truncated_layout_fails(map_repo: Path) -> None:
    (map_repo / "data/layouts/Test/map.bin").write_bytes(b"\x00\x00")
    with pytest.raises(ValueError, match=r"map\.bin"):
        _maps(map_repo)


def test_remake_variable_border_dimensions(map_repo: Path) -> None:
    path = map_repo / "data/layouts/layouts.json"
    row = json.loads(path.read_text("utf-8"))
    row["layouts"][0].update(border_width=1, border_height=3)
    _json(path, row)
    (map_repo / "data/layouts/Test/border.bin").write_bytes(struct.pack("<3H", 5, 6, 7))
    assert _maps(map_repo)["MAP_TEST"].layout.border == (5, 6, 7)


@pytest.mark.pipeline
@pytest.mark.parametrize(
    ("game", "count"),
    list(zip(GEN3_GAMES, (394, 518, 425), strict=True)),
    ids=[game.version_group for game in GEN3_GAMES],
)
def test_all_pinned_maps(game: Game, count: int, source_cache_ready: None) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    repo = open_pret(game, root)
    assert isinstance(repo, Gen3PretRepo)
    assert len(repo.maps) == count
    assert len({(row.group, row.group_index) for row in repo.maps.values()}) == count
    assert all(
        row.layout.primary_tileset in repo.tilesets and row.layout.secondary_tileset in repo.tilesets
        for row in repo.maps.values()
    )
    assert sum(len(row.objects) for row in repo.maps.values()) > 500
    if not repo.remake:
        assert any(connection.direction == "dive" for row in repo.maps.values() for connection in row.connections)
    else:
        assert not any(connection.direction == "dive" for row in repo.maps.values() for connection in row.connections)


@pytest.mark.parametrize(
    ("destination", "number"), [("WARP_ID_NONE", 0), ("WARP_ID_SECRET_BASE", 127), ("WARP_ID_DYNAMIC", 128)]
)
def test_special_warp_ids_are_preserved(map_repo: Path, destination: str, number: int) -> None:
    path = map_repo / "data/maps/Test/map.json"
    row = json.loads(path.read_text("utf-8"))
    row["warp_events"][0]["dest_warp_id"] = destination
    _json(path, row)
    assert _maps(map_repo)["MAP_TEST"].warps[0].target_warp == number


def test_object_hiding_flag_and_local_id_are_preserved(map_repo: Path) -> None:
    path = map_repo / "data/maps/Test/map.json"
    row = json.loads(path.read_text("utf-8"))
    row["object_events"] = [
        dict(
            local_id="LOCALID_TEST",
            graphics_id="OBJ_EVENT_GFX_MOM",
            x=1,
            y=1,
            elevation=3,
            movement_type="MOVEMENT_TYPE_FACE_UP",
            movement_range_x=0,
            movement_range_y=0,
            trainer_type="TRAINER_TYPE_NONE",
            trainer_sight_or_berry_tree_id="0",
            script="Test_EventScript_Mom",
            flag="FLAG_HIDE_TEST_MOM",
        )
    ]
    _json(path, row)
    obj = _maps(map_repo)["MAP_TEST"].objects[0]
    assert obj.value("flag") == "FLAG_HIDE_TEST_MOM"
    assert obj.value("local_id") == "LOCALID_TEST"
    assert obj.value("script") == "Test_EventScript_Mom"


def test_shared_event_cycle_fails(map_repo: Path) -> None:
    path = map_repo / "data/maps/Test/map.json"
    row = json.loads(path.read_text("utf-8"))
    row["shared_events_map"] = "Shared"
    _json(path, row)
    with pytest.raises(ValueError, match="chaînés"):
        _maps(map_repo)


def test_map_group_traversal_is_bounded(map_repo: Path) -> None:
    _json(map_repo / "data/maps/map_groups.json", {"group_order": ["gGroup"], "gGroup": ["Test"] * 257})
    with pytest.raises(ValueError, match="groupe invalide"):
        _maps(map_repo)
