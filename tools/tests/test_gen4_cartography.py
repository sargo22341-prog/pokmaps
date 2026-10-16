"""Assemblages, transports, noms et sprites des deux dépôts DS épinglés."""

from pathlib import Path

import pytest

from pokemaps_data import maps_layout_gen4
from pokemaps_data.games import DIAMOND_PEARL, GEN4_GAMES, PLATINUM
from pokemaps_data.maps import read_map_names
from pokemaps_data.maps_common_gen4 import common_passages
from pokemaps_data.maps_layout_gen4 import camera_cotangent, displays, selected_headers
from pokemaps_data.maps_levels_gen4 import lower_surfaces
from pokemaps_data.maps_lower_gen4 import _skipped_levels
from pokemaps_data.maps_passages_gen4 import scripted_passages, warps
from pokemaps_data.maps_sprites_gen4 import read_field_sprites
from pokemaps_data.maps_travel_gen4 import (
    distortion_connections,
    fly_destinations,
    turnback_connections,
    underground_connections,
)
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_prop_animations import PropAnimations
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parents[1] / ".cache"
pytestmark = pytest.mark.pipeline


@pytest.fixture(scope="module", params=GEN4_GAMES)
def repo(request: pytest.FixtureRequest, source_cache_ready: None) -> Gen4PretRepo:
    game = request.param
    return Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)


def test_selected_maps_are_named_and_unused_copies_are_excluded(repo: Gen4PretRepo) -> None:
    headers = selected_headers(repo)
    assert len(headers) == (503 if repo.platinum else 495)
    assert {header.constant for header in headers.values()} | {"SINNOH"} == read_map_names()[repo.variant].keys()
    assert all(
        ("UNUSED" not in header.constant or header.constant == "MAP_ROUTE_231_UNUSED")
        and "UNKNOWN" not in header.constant
        for header in headers.values()
    )
    if not repo.platinum:
        assert headers[472].location == "SEABREAK_PATH" and headers[472].area == 13
    assert all(camera_cotangent(repo, header) > 0 for header in headers.values())
    assert sum("DISTORTION_WORLD" in header.constant for header in headers.values()) == (10 if repo.platinum else 0)
    for label in ("MtCoronet", "OldChateau", "IronIsland", "GreatMarsh", "StarkMountain"):
        expected = (
            label
            if repo.platinum
            else {
                "MtCoronet": "MT_CORONET",
                "OldChateau": "OLD_CHATEAU",
                "IronIsland": "IRON_ISLAND",
                "GreatMarsh": "GREAT_MARSH",
                "StarkMountain": "STARK_MOUNTAIN",
            }[label]
        )
        assert any(header.location == expected for header in headers.values())


def test_matrices_cover_headers_once_and_blocks_never_overlap(repo: Gen4PretRepo) -> None:
    headers = selected_headers(repo)
    layouts = displays(repo, headers)
    represented = [index for layout in layouts for index in layout.headers]
    assert len(represented) == len(set(represented)) == len(headers)
    assert set(represented) == headers.keys()
    for layout in layouts:
        positions = {(block.column, block.row) for block in layout.blocks}
        assert len(positions) == len(layout.blocks)
        assert all(block.header in layout.headers for block in layout.blocks)
        assert all(block.block != 0xFFFF for block in layout.blocks)
    world = next(layout for layout in layouts if layout.const == "SINNOH")
    # Le prototype gardait une bordure ; le catalogue est rogné aux blocs réellement nommés.
    assert world.bounds == (512, 3072, 14848, 14848)
    marsh = next(layout for layout in layouts if layout.const == "GREAT_MARSH_PLAN")
    assert len(marsh.headers) == 6


def test_missing_french_name_stops_generation(repo: Gen4PretRepo, monkeypatch: pytest.MonkeyPatch) -> None:
    names = read_map_names()
    header = next(iter(selected_headers(repo).values()))
    del names[repo.variant][header.constant]
    monkeypatch.setattr(maps_layout_gen4, "read_map_names", lambda: names)
    with pytest.raises(ValueError, match="noms français DS manquants"):
        selected_headers(repo)


def test_warps_and_scripted_transport_are_complete(repo: Gen4PretRepo) -> None:
    headers = selected_headers(repo)
    result = warps(repo, headers)
    assert len(result) == sum(len(repo.events[header.events].warp_events) for header in headers.values())
    assert sum(passage.kind == "dynamic" for passage in result) == 6
    script = scripted_passages(repo, headers)
    assert sum(passage.kind == "boat" for passage in script) == 8
    assert sum(passage.kind == "elevator" for passage in script) >= 12
    assert all(passage.target is None or passage.target in headers for passage in script)
    assert len(fly_destinations(repo)) == 20
    random = turnback_connections(repo)
    assert len({passage.target for passage in random}) == 21
    assert len(distortion_connections(repo)) == (14 if repo.platinum else 0)
    entrance, exit_passage = underground_connections(repo)
    assert entrance.source is None and entrance.target == 2
    assert exit_passage.source == 2 and exit_passage.target is None and exit_passage.kind == "dynamic"


def test_common_scripts_keep_context_dependent_transports(repo: Gen4PretRepo) -> None:
    passages = common_passages(repo)
    assert len(passages) == (12 if repo.platinum else 11)
    assert all(passage.source is None and passage.evidence for passage in passages)
    assert 510 in {passage.target for passage in passages}
    assert {117, 118} <= {passage.target for passage in passages}


def test_canalave_gym_has_four_superposed_floors_in_each_source(repo: Gen4PretRepo) -> None:
    block = repo.land_block(225 if repo.platinum else 224)
    assert [surface.ceiling for surface in lower_surfaces(block, 0)] == [160 * 4096 - 1, 320 * 4096 - 1, 480 * 4096 - 1]


def test_negative_house_bdhc_plane_is_not_exposed_as_a_basement(repo: Gen4PretRepo) -> None:
    skipped = _skipped_levels(repo)
    assert len(skipped) == (1 if repo.platinum else 0)
    header = repo.headers[423]
    matrix = repo.matrices[header.matrix]
    blocks = [value for row in matrix.blocks for value in row if value != 0xFFFF]
    surfaces = [surface for block in blocks for surface in lower_surfaces(repo.land_block(block), 0)]
    if repo.platinum:
        assert header.constant in skipped and surfaces and all(surface.ceiling < 0 for surface in surfaces)
    else:
        assert surfaces == []


def test_fly_destinations_really_differ_between_the_two_sources(source_cache_ready: None) -> None:
    platinum = Gen4PretRepo(pret_dir(CACHE, PLATINUM.pret_repo), PLATINUM.pret_versions)
    diamond = Gen4PretRepo(pret_dir(CACHE, DIAMOND_PEARL.pret_repo), DIAMOND_PEARL.pret_versions)
    pt = [(row.target, row.target_x, row.target_z) for row in fly_destinations(platinum)]
    dp = [(row.target, row.target_x, row.target_z) for row in fly_destinations(diamond)]
    assert len(pt) == len(dp) == 20 and pt != dp
    assert pt[0] == dp[0] == (411, 116, 886)


def test_133_shared_npc_frames_are_identical_and_three_are_not(source_cache_ready: None) -> None:
    images = []
    for game in GEN4_GAMES:
        repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
        used = {event.graphics for events in repo.events.values() for event in events.object_events}
        images.append({sprite.graphics: sprite.image for sprite in read_field_sprites(repo, used)})
    common = images[0].keys() & images[1].keys()
    different = {
        key
        for key in common
        if images[0][key].size != images[1][key].size or images[0][key].tobytes() != images[1][key].tobytes()
    }
    assert len(common) == 136
    assert different == {148, 206, 207}
    for sprites in images:
        assert sprites[156].size == sprites[160].size == (64, 64)


def test_automatic_texture_animations_are_sampled_at_frame_zero(repo: Gen4PretRepo) -> None:
    animations = PropAnimations(repo)
    blocks = {block.block for layout in displays(repo, selected_headers(repo)) for block in layout.blocks}
    models = {prop.model for index in blocks for prop in repo.land_block(index).props}
    changed = set()
    for index in models:
        source = repo.prop_model(index)
        if animations.first_frame(index, source) != source:
            changed.add(index)
    assert changed == ({299} if repo.platinum else set())
    if repo.platinum:
        model = animations.first_frame(299, repo.prop_model(299)).models[0]
        assert {material.texture for material in model.materials} >= {"c3_s03c.4", "c3_s03b.16"}
