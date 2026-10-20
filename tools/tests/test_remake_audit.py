"""Non-régression des omissions constatées dans Rouge Feu et Vert Feuille."""

import re
import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_identifiers import species_identifier
from pokemaps_data.sources import pret_dir

_VERSIONS = ["firered", "leafgreen"]


def _offers(db: sqlite3.Connection, version: str, kind: str) -> list[tuple[str, str, str | None]]:
    return db.execute(
        """SELECT m.identifier, coalesce(p.identifier, i.identifier), w.identifier FROM npc_offer n
           JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
           LEFT JOIN item i ON i.id = n.item_id LEFT JOIN pokemon w ON w.id = n.wanted_pokemon_id
           WHERE v.identifier = ? AND n.kind = ?""",
        (version, kind),
    ).fetchall()


@pytest.mark.parametrize("version", _VERSIONS)
def test_cinnabar_lab_trades_survive_the_party_menu(db: sqlite3.Connection, version: str) -> None:
    trades = _offers(db, version, "trade")
    assert len(trades) == 9
    assert {
        ("cinnabar-island-pokemon-lab-lounge", "electrode", "raichu"),
        ("cinnabar-island-pokemon-lab-lounge", "tangela", "venonat"),
        ("cinnabar-island-pokemon-lab-experiment-room", "seel", "ponyta"),
    } <= set(trades)


@pytest.mark.parametrize("version", _VERSIONS)
def test_scene_and_size_record_gifts_are_displayed(db: sqlite3.Connection, version: str) -> None:
    gifts = {(place, item) for place, item, _ in _offers(db, version, "gift_item")}
    assert {
        ("cerulean-city", "fame-checker"),
        ("viridian-city-mart", "oaks-parcel"),
        ("one-island-pokemon-center-1f", "meteorite"),
        ("one-island-pokemon-center-1f", "tri-pass"),
        ("route12-fishing-house", "net-ball"),
        ("six-island-water-path-house1", "nest-ball"),
    } <= gifts


@pytest.mark.parametrize("version", _VERSIONS)
def test_rival_battles_have_one_team_per_player_starter(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT m.identifier, o.name_fr, group_concat(DISTINCT t.variant_pokemon_id) FROM map_object o
           JOIN map m ON m.id = o.map_id JOIN version v ON v.id = o.version_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE v.identifier = ? AND o.name_fr LIKE 'Rival%' GROUP BY o.id""",
        (version,),
    ).fetchall()
    assert sorted((place, name) for place, name, _ in rows) == [
        ("cerulean-city", "Rival"),
        ("pallet-town-professor-oaks-lab", "Rival"),
        ("pokemon-league-champions-room", "Rival"),
        ("pokemon-tower-2f", "Rival"),
        ("route22", "Rival"),
        ("silph-co-7f", "Rival"),
        ("ssanne-2f-corridor", "Rival"),
    ]
    assert all(sorted(int(mon) for mon in starters.split(",")) == [1, 4, 7] for _, _, starters in rows)


@pytest.mark.parametrize("version", _VERSIONS)
def test_leaders_and_elite_four_are_named(db: sqlite3.Connection, version: str) -> None:
    names = {
        row[0]
        for row in db.execute(
            """SELECT o.name_fr FROM map_object o JOIN version v ON v.id = o.version_id
               WHERE v.identifier = ? AND o.kind = 'trainer' AND o.trainer_class IN
               ('TRAINER_CLASS_LEADER', 'TRAINER_CLASS_ELITE_FOUR', 'TRAINER_CLASS_BOSS')""",
            (version,),
        )
    }
    leaders = {"Pierre", "Ondine", "Major Bob", "Érika", "Koga", "Morgane", "Auguste", "Giovanni"}
    elite = {"Olga", "Aldo", "Agatha", "Peter"}
    assert names == leaders | elite | {f"{name} (revanche)" for name in elite}


@pytest.mark.parametrize("version", _VERSIONS)
def test_game_corner_coins_and_berry_forest_hypno_are_on_the_map(db: sqlite3.Connection, version: str) -> None:
    coins = db.execute(
        """SELECT sum(cast(o.name_fr AS INTEGER)), count(*) FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id JOIN item i ON i.id = o.item_id
           WHERE v.identifier = ? AND m.identifier = 'celadon-city-game-corner' AND i.identifier = 'coin'""",
        (version,),
    ).fetchone()
    assert coins == (260, 12)
    hypno = db.execute(
        """SELECT m.identifier, o.level FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id WHERE v.identifier = ? AND o.kind = 'pokemon' AND o.pokemon_id = 97""",
        (version,),
    ).fetchall()
    assert hypno == [("three-island-berry-forest", 30)]


@pytest.mark.parametrize("version", _VERSIONS)
def test_magikarp_seller_and_trades_are_annotated_once(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT em.identifier, l.identifier, e.note_fr FROM encounter e JOIN version v ON v.id = e.version_id
           JOIN encounter_method em ON em.id = e.method_id JOIN location_area la ON la.id = e.location_area_id
           JOIN location l ON l.id = la.location_id
           WHERE v.identifier = ? AND (em.identifier = 'npc-trade' OR e.pokemon_id = 129 AND em.identifier = 'gift')""",
        (version,),
    ).fetchall()
    assert [place for method, place, _ in rows if method == "gift"] == ["kanto-route-4"]
    trades = [note for method, _, note in rows if method == "npc-trade"]
    assert len(trades) == 9
    assert all(note and note.startswith("Échange contre ") for note in trades)


@pytest.mark.pipeline
@pytest.mark.parametrize("version", _VERSIONS)
def test_every_scripted_kanto_battle_is_displayed(
    db: sqlite3.Connection,
    version: str,
    source_cache_ready: None,
) -> None:
    game = next(game for game in GEN3_GAMES if game.version_group == "firered-leafgreen")
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    repo = Gen3PretRepo(root, game.pret_versions)
    sources = [*sorted((root / "data/maps").glob("*/scripts.inc")), root / "data/scripts/trainers.inc"]
    battled = {
        trainer
        for path in sources
        for trainer in re.findall(r"trainerbattle\w*\s+(?:\w+,\s*)?(TRAINER_\w+)", path.read_text("utf-8"))
    }
    species = dict(db.execute("SELECT identifier, id FROM pokemon"))
    rows = db.execute(
        """SELECT o.id, t.team, t.pokemon_id, t.level FROM map_object o JOIN version v ON v.id = o.version_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id WHERE v.identifier = ? ORDER BY o.id, t.team, t.slot""",
        (version,),
    ).fetchall()
    teams: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for actor, team, mon, level in rows:
        teams.setdefault((actor, team), []).append((mon, level))
    displayed = {tuple(party) for party in teams.values()}
    for trainer in sorted(battled):
        party = tuple(
            (species[species_identifier(mon.species.removeprefix("SPECIES_"))], mon.level)
            for mon in repo.trainers[version][trainer].party
        )
        assert party in displayed, trainer
