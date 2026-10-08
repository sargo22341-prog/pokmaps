"""Assemblage des zones d'un niveau : pixels, coordonnées et erreurs éditoriales."""

import csv
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data import maps_plans
from pokemaps_data.games import GAMES, Game
from pokemaps_data.maps import renderer
from pokemaps_data.maps_layout import GameMaps, read_layout_curation
from pokemaps_data.maps_plans import build_plans, read_plans
from pokemaps_data.pret_reader import open_pret
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"


@pytest.mark.parametrize("game", GAMES, ids=lambda game: game.version_group)
def test_plan_preserves_every_source_pixel_and_coordinate(game: Game, source_cache_ready: None) -> None:
    layout = GameMaps(open_pret(game, pret_dir(CACHE, game.pret_repo)), game, read_layout_curation())
    painter = renderer(layout)
    assert layout.plans
    for plan in layout.plans.values():
        image = painter.render(plan.const).image
        assert image.mode == "RGBA"
        for part in plan.parts:
            source = painter.render(part.map).image.convert("RGBA")
            crop = image.crop((part.x, part.y, part.x + source.width, part.y + source.height))
            assert crop.tobytes() == source.tobytes(), part.map
            assert layout.point(part.map, 0, 0) == (part.x + 8, part.y + 8)
            assert layout.placements[part.map].display == plan.const
            assert part.map not in layout.display_maps


def test_safari_houses_stay_separate_and_plan_spots_stay_on_their_zone(db: sqlite3.Connection) -> None:
    for group in (1, 2):
        plan_id = group * 1000 + 900
        children = set(db.execute("SELECT identifier FROM map WHERE parent_map_id = ?", (plan_id,)))
        assert children == {(f"safari-zone-{zone}",) for zone in ("north", "east", "west", "center")}
        houses = db.execute(
            """SELECT parent_map_id, level_count FROM map
               WHERE version_group_id = ? AND identifier LIKE 'safari-zone-%house'""",
            (group,),
        ).fetchall()
        assert len(houses) == 5
        assert all(parent is None and levels > 0 for parent, levels in houses)
    assert not db.execute(
        """SELECT s.id FROM map_spot s JOIN map m ON m.id = s.map_id
           WHERE s.x < m.x OR s.y < m.y OR s.x >= m.x + m.width OR s.y >= m.y + m.height"""
    ).fetchall()


def test_captains_room_is_on_the_third_deck_not_the_second(db: sqlite3.Connection) -> None:
    floors = db.execute(
        """SELECT parent.identifier FROM map room JOIN map parent ON parent.id = room.parent_map_id
           WHERE room.identifier = 'ss-anne-captains-room' ORDER BY room.version_group_id"""
    ).fetchall()
    assert floors == [("ss-anne-3f-plan",), ("ss-anne-3f-plan",)]


def test_overlapping_or_unreachable_parts_fail(gold_silver_maps: GameMaps) -> None:
    layout = gold_silver_maps
    plan = layout.plans["MOUNT_MORTAR_1F_PLAN"]
    first, second = plan.parts
    with pytest.raises(ValueError, match="recouvre"):
        build_plans((first, replace(second, x=first.x, y=first.y)), layout.maps, set(layout.parents))
    with pytest.raises(ValueError, match="non accessible"):
        build_plans((replace(first, map="NEW_BARK_TOWN"),), layout.maps, set(layout.parents))
    with pytest.raises(ValueError, match="contradictoire"):
        build_plans((first, replace(second, name="Autre nom")), layout.maps, set(layout.parents))


def test_invalid_curation_is_rejected_at_read_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    part = read_plans()[0]
    monkeypatch.setattr(maps_plans, "DATA_DIR", tmp_path)
    path = tmp_path / "map_plans.csv"
    fields = ("family", "plan", "number", "name_fr", "map", "x", "y")
    row = dict(zip(fields, (part.family, part.plan, part.number, part.name, part.map, 0, 0), strict=True))
    for change in ({"x": -1}, {"number": 999}, {"name_fr": ""}, {"family": "inconnue"}):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fields)
            writer.writeheader()
            writer.writerow(row | change)
        with pytest.raises(ValueError, match=r"map_plans\.csv"):
            read_plans()
