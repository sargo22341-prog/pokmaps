"""Les repères utiles restent visibles sans doublons de scénario ni points blancs décoratifs."""

import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemaps_data.character_actors_gen4 import CharacterActor
from pokemaps_data.games import GEN4_GAMES, Game
from pokemaps_data.maps_actor_positions_gen4 import _clears_frame
from pokemaps_data.maps_battles_gen4 import _teams, merge_story_actors
from pokemaps_data.maps_berries_gen4 import initial_berries
from pokemaps_data.maps_characters import ObjectRow
from pokemaps_data.maps_characters_gen4 import _display_actors
from pokemaps_data.maps_layout_gen4 import selected_headers
from pokemaps_data.maps_underground_actors_gen4 import underground_positions
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_trainers import Gen4Trainer, Gen4TrainerPokemon
from pokemaps_data.pret_models import VariantKind
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import CHECKS


def _trainer(number: int, species: str) -> Gen4Trainer:
    mon = Gen4TrainerPokemon(species, 0, 5, (), None, 0, False)
    return Gen4Trainer(number, None, "TRAINER_CLASS_RIVAL", "Cedric", False, (), (mon,))


def test_starter_branches_share_one_actor_and_keep_all_teams() -> None:
    builder = SimpleNamespace(species={387: {"identifier": "turtwig"}, 390: {"identifier": "chimchar"}})
    row = ObjectRow("MAP", "trainer", 0, 0, "148", None, None, None, None)
    trainers = {1: _trainer(1, "SPECIES_PIPLUP"), 2: _trainer(2, "SPECIES_TURTWIG")}
    _teams(builder, row, trainers, [(1, 387), (2, 390)])
    assert not row.party and not row.rematches
    assert [(kind, species) for kind, species, _ in row.variants] == [
        (VariantKind.PLAYER_STARTER, "turtwig"),
        (VariantKind.PLAYER_STARTER, "chimchar"),
    ]


def test_partner_starter_does_not_duplicate_an_unchanged_opponent() -> None:
    row = ObjectRow("MAP", "trainer", 0, 0, "121", None, None, None, None)
    _teams(SimpleNamespace(), row, {1: _trainer(1, "SPECIES_PURUGLY")}, [(1, 387), (1, 390), (1, 393)])
    assert len(row.party) == 1 and not row.variants and not row.rematches


def test_each_starter_keeps_its_own_rematch_numbers() -> None:
    builder = SimpleNamespace(species={387: {"identifier": "turtwig"}, 390: {"identifier": "chimchar"}})
    row = ObjectRow("MAP", "trainer", 0, 0, "148", None, None, None, None)
    trainers = {number: _trainer(number, "SPECIES_PIPLUP") for number in range(1, 5)}
    _teams(builder, row, trainers, [(1, 387), (2, 387), (3, 390), (4, 390)])
    assert row.variant_rematches == {2: 1, 4: 1}
    assert len(row.variants) == 4 and not row.party


def test_a_stronger_team_tested_first_is_still_displayed_as_a_rematch() -> None:
    row = ObjectRow("MAP", "trainer", 0, 0, "148", None, None, None, None)
    initial = _trainer(1, "SPECIES_PIPLUP")
    stronger = replace(_trainer(2, "SPECIES_PIPLUP"), party=(replace(initial.party[0], level=80),))
    _teams(SimpleNamespace(), row, {1: initial, 2: stronger}, [(2, None), (1, None)])
    assert row.party[0][1] == 5 and row.rematches[0][0][1] == 80


def test_story_poses_merge_without_merging_two_real_pupils() -> None:
    actors = [
        ObjectRow("MAP", "npc", x, 0, sprite, None, None, None, None)
        for x, sprite in [(0, "148"), (16, "148"), (32, "3"), (64, "3")]
    ]
    result = merge_story_actors(actors)
    assert [row.sprite for row in result] == ["148", "3", "3"]


def test_an_item_replaces_its_raw_ball_but_keeps_a_character_on_the_same_cell() -> None:
    ball = CharacterActor("ball", "MAP", 0, 0, 87, 1, 1, 1, 7000, ())
    pupil = CharacterActor("pupil", "MAP", 1, 1, 3, 1, 1, 0, 1, ())
    catalog = SimpleNamespace(
        actors=SimpleNamespace(actors=(ball, pupil)),
        headers={1: "MAP"},
        items=(SimpleNamespace(header=1, x=1, z=1, kind="item"),),
        fixed=(),
        names=SimpleNamespace(sprites={87: ("Poké Ball", "object"), 3: ("Élève", "person")}),
    )
    assert _display_actors(catalog) == [pupil]


@pytest.mark.parametrize(
    "point,clear", [((0, 0), False), ((16, 0), False), ((0, 16), False), ((24, 0), True), ((0, 32), True)]
)
def test_character_frames_do_not_touch(point: tuple[int, int], clear: bool) -> None:
    assert _clears_frame(point, (0, -24, 20, 4), [(0, -24, 20, 4)]) == clear


def test_wide_sprite_needs_more_room_than_a_pupil() -> None:
    assert not _clears_frame((24, 0), (0, -24, 29, 4), [(0, -24, 29, 4)])
    assert _clears_frame((33, 0), (0, -24, 29, 4), [(0, -24, 29, 4)])


def test_distributed_maps_have_no_empty_marker(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "repère sans image ni interaction")
    assert not db.execute(query).fetchall()
    db.execute(
        "UPDATE map_object SET sprite = NULL WHERE id = (SELECT id FROM map_object WHERE kind = 'npc' "
        "AND id NOT IN (SELECT map_object_id FROM npc_offer) LIMIT 1)"
    )
    assert db.execute(query).fetchall()


@pytest.mark.parametrize("group", [8, 9])
def test_rival_uses_one_sprite_and_three_starter_choices(db: sqlite3.Connection, group: int) -> None:
    rows = db.execute(
        """SELECT o.id, o.sprite, count(DISTINCT t.variant_pokemon_id) FROM map_object o
           JOIN map m ON m.id = o.map_id JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE m.version_group_id = ? AND m.identifier LIKE '%route-203' AND o.kind = 'trainer'
           AND o.sprite = '148' GROUP BY o.id""",
        (group,),
    ).fetchall()
    assert len(rows) == 1 and rows[0][1:] == ("148", 3)


@pytest.mark.parametrize("group", [8, 9])
def test_initial_berries_replace_the_bare_soil_markers(db: sqlite3.Connection, group: int) -> None:
    berries = db.execute(
        """SELECT count(*) FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id
           JOIN map m ON m.id = o.map_id WHERE m.version_group_id = ? AND n.kind = 'fruit_tree'""",
        (group,),
    ).fetchone()[0]
    assert berries == 118
    assert not db.execute(
        "SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id "
        "WHERE m.version_group_id = ? AND o.name_fr = 'Sol meuble' "
        "AND o.id NOT IN (SELECT map_object_id FROM npc_offer WHERE kind = 'fruit_tree')",
        (group,),
    ).fetchall()


@pytest.mark.parametrize("group", [8, 9])
def test_jubilife_keeps_two_galactic_opponents(db: sqlite3.Connection, group: int) -> None:
    rows = db.execute(
        """SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id = ? AND m.identifier IN ('jublife', 'header-jubilife-city')
           AND o.kind = 'trainer' AND o.sprite = '124'""",
        (group,),
    ).fetchall()
    assert len(rows) == 2


def test_variant_rematch_validation_rejects_a_missing_first_rematch(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "revanches de variante non consécutives")
    assert not db.execute(query).fetchall()
    db.execute("UPDATE trainer_pokemon SET rematch = 2 WHERE variant_kind IS NOT NULL AND rematch = 1")
    assert db.execute(query).fetchall()


@pytest.mark.parametrize("game", GEN4_GAMES, ids=lambda game: game.version_group)
def test_source_plantations_and_merchant_positions_are_complete(game: Game, source_cache_ready: None) -> None:
    repo = Gen4PretRepo(pret_dir(Path(__file__).parents[1] / ".cache", game.pret_repo), game.pret_versions)
    berries = initial_berries(repo)
    patches = [
        event.data[0]
        for header in selected_headers(repo).values()
        for event in repo.events[header.events].object_events
        if event.graphics == 100
    ]
    assert sorted(patches) == list(range(len(berries)))
    assert berries[0] == ("ITEM_ORAN_BERRY", 1)
    vendors = underground_positions(repo, repo.headers[2])
    assert len(vendors) == 20 and vendors[17] == (40, 471)
