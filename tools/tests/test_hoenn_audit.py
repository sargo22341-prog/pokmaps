"""Non-régression des omissions constatées dans Rubis, Saphir et Émeraude."""

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_trainers import read_learnsets
from pokemaps_data.pret_identifiers import species_identifier
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import CHECKS


@pytest.mark.parametrize("version,count", [("ruby", 4), ("sapphire", 4), ("emerald", 5)])
def test_flora_has_three_player_starter_teams(db: sqlite3.Connection, version: str, count: int) -> None:
    actors = db.execute(
        """SELECT o.id FROM map_object o JOIN version v ON v.id = o.version_id
           WHERE v.identifier = ? AND o.kind = 'trainer' AND o.name_fr = 'Flora'""",
        (version,),
    ).fetchall()
    assert len(actors) == count
    for (actor,) in actors:
        teams = db.execute(
            "SELECT DISTINCT variant_kind, variant_pokemon_id FROM trainer_pokemon WHERE map_object_id = ?",
            (actor,),
        ).fetchall()
        assert set(teams) == {("player-starter", mon) for mon in (252, 255, 258)}


@pytest.mark.parametrize(
    "version,champion", [("ruby", "Pierre Rochard"), ("sapphire", "Pierre Rochard"), ("emerald", "Marc")]
)
def test_champion_and_wally_story_teams_exist(db: sqlite3.Connection, version: str, champion: str) -> None:
    rows = db.execute(
        """SELECT m.identifier, o.name_fr, count(*), min(t.level), max(t.level)
           FROM map_object o JOIN version v ON v.id = o.version_id JOIN map m ON m.id = o.map_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE v.identifier = ? AND t.team = 1 AND
           (m.identifier = 'ever-grande-city-champions-room' OR o.name_fr = 'Timmy')
           GROUP BY o.id""",
        (version,),
    ).fetchall()
    assert any(name == champion and size == 6 for _, name, size, _, _ in rows)
    assert any(name == "Timmy" and size == 5 and (low, high) == (41, 45) for _, name, size, low, high in rows)


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_required_scene_gifts_are_available(db: sqlite3.Connection, version: str) -> None:
    items = {
        row[0]
        for row in db.execute(
            """SELECT i.identifier FROM npc_offer n JOIN item i ON i.id = n.item_id
           JOIN map_object o ON o.id = n.map_object_id JOIN version v ON v.id = o.version_id
           WHERE v.identifier = ? AND n.kind = 'gift_item'""",
            (version,),
        )
    }
    assert {"hm03", "hm04", "hm08", "dowsing-machine", "letter", "go-goggles", "poke-ball"} <= items
    assert {"spelon-berry", "pamtre-berry", "watmel-berry", "durin-berry", "belue-berry"} <= items
    assert ("magma-emblem" if version == "emerald" else "red-orb" if version == "ruby" else "blue-orb") in items


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_voltorb_and_electrode_are_exact_fixed_encounters(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT l.identifier, p.identifier, e.quantity FROM encounter e
           JOIN version v ON v.id = e.version_id JOIN pokemon p ON p.id = e.pokemon_id
           JOIN encounter_method em ON em.id = e.method_id
           JOIN location_area a ON a.id = e.location_area_id JOIN location l ON l.id = a.location_id
           WHERE v.identifier = ? AND em.identifier = 'static' AND p.id IN (100, 101)""",
        (version,),
    ).fetchall()
    assert Counter((place, mon) for place, mon, _ in rows) == {
        ("new-mauville", "voltorb"): 1,
        ("team-magma-hideout" if version == "ruby" else "team-aqua-hideout", "electrode"): 1,
    }
    assert sorted(quantity for _, _, quantity in rows) == [2, 3]
    assert (
        db.execute(
            """SELECT count(*) FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id WHERE v.identifier = ?
           AND m.identifier = 'new-mauville-inside' AND o.pokemon_id = 100 AND o.kind = 'pokemon'""",
            (version,),
        ).fetchone()[0]
        == 3
    )


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_rematches_and_shared_gym_battle(db: sqlite3.Connection, version: str) -> None:
    count = db.execute(
        """SELECT count(DISTINCT o.id) FROM map_object o JOIN version v ON v.id = o.version_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id WHERE v.identifier = ? AND t.rematch IS NOT NULL""",
        (version,),
    ).fetchone()[0]
    assert count >= 50
    assert (
        db.execute(
            """SELECT count(*) FROM map_object o JOIN version v ON v.id = o.version_id
           WHERE v.identifier = ? AND o.name_fr = 'Lévy et Tatia' AND o.kind = 'trainer'""",
            (version,),
        ).fetchone()[0]
        == 1
    )


def test_gift_pokemon_and_trade_conditions(db: sqlite3.Connection) -> None:
    rows = db.execute(
        """SELECT p.identifier, group_concat(s.description_fr, ' ') FROM npc_offer n
           JOIN pokemon p ON p.id = n.pokemon_id JOIN npc_offer_story s ON s.npc_offer_id = n.id
           JOIN map_object o ON o.id = n.map_object_id JOIN version v ON v.id = o.version_id
           WHERE v.identifier = 'emerald' AND p.id IN (152, 155, 158, 374) GROUP BY n.id""",
    ).fetchall()
    assert {mon for mon, _ in rows} >= {"chikorita", "cyndaquil", "totodile", "beldum"}
    assert all("Ligue" in story if mon == "beldum" else "200" in story for mon, story in rows)


def test_move_version_validation_detects_another_group(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "version spécifique d'apprentissage invalide")
    assert db.execute(query).fetchall() == []
    db.execute("UPDATE pokemon_move SET version_id = 1 WHERE pokemon_id = 386 AND version_group_id = 7")
    assert db.execute(query).fetchall()


def test_fixed_quantity_validation_detects_a_duplicate(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "quantité de Voltorbe fixe de New Lavandia invalide")
    assert db.execute(query).fetchall() == []
    db.execute("""UPDATE encounter SET quantity = 6 WHERE pokemon_id = 100
                  AND method_id = (SELECT id FROM encounter_method WHERE identifier = 'static')""")
    assert db.execute(query).fetchall()


@pytest.mark.parametrize("version", ["ruby", "sapphire", "emerald"])
def test_kecleon_script_paths_do_not_duplicate_the_bridge_encounter(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT em.identifier, sum(e.quantity) FROM encounter e JOIN version v ON v.id = e.version_id
           JOIN encounter_method em ON em.id = e.method_id WHERE v.identifier = ? AND e.pokemon_id = 352
           AND em.identifier IN ('static', 'devon-scope') GROUP BY em.id""",
        (version,),
    ).fetchall()
    assert rows == [("devon-scope", 8)]


@pytest.mark.parametrize("version", ["firered", "leafgreen"])
def test_remake_fixed_reconciliation_preserves_the_pokeflute(db: sqlite3.Connection, version: str) -> None:
    rows = db.execute(
        """SELECT em.identifier, sum(e.quantity) FROM encounter e JOIN version v ON v.id = e.version_id
           JOIN encounter_method em ON em.id = e.method_id WHERE v.identifier = ? AND e.pokemon_id = 143
           GROUP BY em.id""",
        (version,),
    ).fetchall()
    assert rows == [("pokeflute", 2)]
    assert (
        db.execute(
            """SELECT sum(e.quantity) FROM encounter e JOIN version v ON v.id = e.version_id
           WHERE v.identifier = ? AND e.pokemon_id = 146""",
            (version,),
        ).fetchone()[0]
        == 1
    )


@pytest.mark.pipeline
@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_deoxys_level_moves_match_each_pinned_cartridge(
    db: sqlite3.Connection,
    game: Game,
    source_cache_ready: None,
) -> None:
    cache = Path(__file__).resolve().parents[1] / ".cache"
    repo = Gen3PretRepo(pret_dir(cache, game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        expected = {
            (level, move.removeprefix("MOVE_").lower().replace("_", "-"))
            for level, move in read_learnsets(repo, version)["SPECIES_DEOXYS"]
        }
        actual = set(
            db.execute(
                """SELECT pm.level, m.identifier FROM pokemon_move pm JOIN move m ON m.id = pm.move_id
               JOIN version v ON v.version_group_id = pm.version_group_id
               WHERE v.identifier = ? AND pm.pokemon_id = 386 AND pm.method = 'level-up'
               AND (pm.version_id IS NULL OR pm.version_id = v.id)""",
                (version,),
            )
        )
        assert actual == expected


@pytest.mark.pipeline
@pytest.mark.parametrize("game", GEN3_GAMES[:2], ids=lambda game: game.version_group)
def test_all_pinned_hoenn_rematch_series_are_displayed(
    db: sqlite3.Connection,
    game: Game,
    source_cache_ready: None,
) -> None:
    cache = Path(__file__).resolve().parents[1] / ".cache"
    repo = Gen3PretRepo(pret_dir(cache, game.pret_repo), game.pret_versions)
    species = dict(db.execute("SELECT identifier, id FROM pokemon"))
    for version, _ in game.pret_versions:
        rows = db.execute(
            """SELECT o.id, t.team, t.pokemon_id, t.level FROM map_object o
               JOIN version v ON v.id = o.version_id JOIN trainer_pokemon t ON t.map_object_id = o.id
               WHERE v.identifier = ? ORDER BY o.id, t.team, t.slot""",
            (version,),
        ).fetchall()
        displayed: dict[int, dict[int, list[tuple[int, int]]]] = {}
        for actor, team, mon, level in rows:
            displayed.setdefault(actor, {}).setdefault(team, []).append((mon, level))
        actual = {tuple(tuple(party) for _, party in sorted(teams.items())) for teams in displayed.values()}
        for series in repo.rematches[version]:
            expected = tuple(
                tuple(
                    (species[species_identifier(mon.species.removeprefix("SPECIES_"))], mon.level)
                    for mon in repo.trainers[version][team.trainer].party
                )
                for team in series.teams
            )
            assert expected in actual, (version, series.teams[0].trainer)
