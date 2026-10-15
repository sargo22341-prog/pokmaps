"""Les personnages affichés laissent libres les passages de toutes les versions."""

import sqlite3
from dataclasses import replace

import pytest

from pokemaps_data.games import EMERALD
from pokemaps_data.maps_actor_positions import clear_actor_passages, clears_passages
from pokemaps_data.maps_characters import ObjectRow
from pokemaps_data.maps_layout import Placed
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_maps import Gen3Layout, Gen3Map, Gen3Warp
from pokemaps_data.validate import CHECKS


def _maps(cells: tuple[int, ...]) -> Gen3GameMaps:
    layout = Gen3Layout("LAYOUT_TEST", 5, 5, "Primary", "Secondary", cells, 1, 1, (0,))
    current = Gen3Map(
        "MAP_TEST",
        "Test",
        1,
        0,
        0,
        layout,
        "MAP_TYPE_INDOOR",
        "MAPSEC_TEST",
        (),
        (Gen3Warp(1, 1, "MAP_TEST", 1, 0),),
        (),
        (),
        (),
        None,
        None,
        (),
    )
    maps = Gen3GameMaps.__new__(Gen3GameMaps)
    maps.repo = Gen3PretRepo.__new__(Gen3PretRepo)
    maps.game = EMERALD
    maps.maps = {"MAP_TEST": current}
    maps.__dict__["placements"] = {"MAP_TEST": Placed("MAP_TEST", 0, 0)}
    return maps


def _actor(x: int = 24, y: int = 24, key: str = "actor") -> ObjectRow:
    return ObjectRow("MAP_TEST", "npc", x, y, "sprite", None, None, None, None, key=key)


def test_actor_moves_to_an_empty_walkable_cell_and_keeps_its_offers() -> None:
    maps = _maps((1024,) * 5 + (0,) * 5 + (1024,) * 15)
    actor, neighbor = _actor(), _actor(40, 24, "neighbor")
    moved, retained = clear_actor_passages(maps, [actor, neighbor])
    assert (moved.x, moved.y) == (56, 24)
    assert moved.key == actor.key and moved.offers == actor.offers
    assert retained == neighbor
    assert (actor.x, actor.y) == (24, 24)


def test_alternative_teams_of_the_same_actor_share_the_new_position() -> None:
    maps = _maps((0,) * 25)
    first, second = clear_actor_passages(maps, [_actor(), _actor()])
    assert (first.x, first.y) == (second.x, second.y) != (24, 24)


def test_no_free_cell_reports_the_map_and_actor() -> None:
    with pytest.raises(ValueError, match="MAP_TEST:actor"):
        clear_actor_passages(_maps((1024,) * 25), [_actor()])


def test_repositioning_keeps_database_row_order() -> None:
    maps = _maps((0,) * 25)
    maps.maps["MAP_OTHER"] = replace(maps.maps["MAP_TEST"], const="MAP_OTHER")
    maps.placements["MAP_OTHER"] = Placed("MAP_OTHER", 0, 0)
    actors = [_actor(8, 8), replace(_actor(8, 8), map_const="MAP_OTHER"), _actor(40, 40)]
    assert clear_actor_passages(maps, actors) == actors


def test_outdoor_actor_never_moves_into_the_upper_half_of_a_door() -> None:
    maps = _maps((0,) * 25)
    maps.maps["MAP_TEST"] = replace(maps.maps["MAP_TEST"], map_type="MAP_TYPE_CITY")
    first, second = clear_actor_passages(maps, [_actor(), replace(_actor(), version="emerald")])
    assert clears_passages((first.x, first.y), {(24, 24)})
    assert (first.x, first.y) == (second.x, second.y)


@pytest.mark.parametrize("dx,dy", [(0, 16), (0, -16), (16, 0), (-16, 0), (16, 16), (-16, 16)])
def test_one_tile_shift_does_not_clear_the_sprite_from_the_passage(dx: int, dy: int) -> None:
    assert not clears_passages((24 + dx, 24 + dy), {(24, 24)})


def test_two_tiles_below_still_leave_a_tall_sprite_too_close() -> None:
    assert not clears_passages((24, 56), {(24, 24)})
    assert clears_passages((24, 72), {(24, 24)})
    assert clears_passages((56, 24), {(24, 24)})


def test_fixed_actor_near_a_door_is_preserved() -> None:
    actor = _actor(40, 24)
    assert clear_actor_passages(_maps((0,) * 25), [actor]) == [actor]


def test_actor_never_crosses_a_wall_to_reach_a_free_cell() -> None:
    cells = [1024] * 25
    cells[6], cells[8] = 0, 0
    with pytest.raises(ValueError, match="MAP_TEST:actor"):
        clear_actor_passages(_maps(tuple(cells)), [_actor()])


def test_distributed_characters_leave_passages_free(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "personnage sur un passage")
    assert db.execute(query).fetchall() == []


def test_validation_rejects_a_character_on_a_warp(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "personnage sur un passage")
    db.execute("SAVEPOINT actor_position")
    try:
        db.execute(
            """UPDATE map_object SET x = w.x, y = w.y FROM map_warp w
               WHERE map_object.id = (SELECT o.id FROM map_object o
               WHERE o.kind = 'npc' AND o.map_id = w.map_id LIMIT 1)"""
        )
        assert db.execute(query).fetchall()
    finally:
        db.execute("ROLLBACK TO actor_position")
        db.execute("RELEASE actor_position")
