"""Régressions des équipes par version et des quatre combats Rocket de Jaune."""

import sqlite3
from pathlib import Path

import pytest

from pokemaps_data.games import EMERALD, RUBY_SAPPHIRE, Game
from pokemaps_data.hoenn_team_battles import team_battle
from pokemaps_data.hoenn_team_graphics import apply_team_graphics, team_graphics
from pokemaps_data.pret import PretRepo
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate_team_battles import validate_team_battles


def test_distributed_team_battles(db: sqlite3.Connection) -> None:
    assert validate_team_battles(db) == []
    expected = {
        "mt-moon-b2f": [("ekans", 14), ("meowth", 14), ("koffing", 14)],
        "rocket-hideout-b4f": [("koffing", 25), ("meowth", 25), ("ekans", 25)],
        "pokemon-tower-7f": [("meowth", 27), ("arbok", 27), ("weezing", 27)],
        "silph-co-11f": [("weezing", 31), ("arbok", 31), ("meowth", 31)],
    }
    for label, party in expected.items():
        assert (
            db.execute(
                """SELECT p.identifier, t.level FROM trainer_pokemon t
               JOIN pokemon p ON p.id = t.pokemon_id JOIN map_object o ON o.id = t.map_object_id
               JOIN map m ON m.id = o.map_id WHERE m.identifier = ? AND o.sprite = 'jessie' ORDER BY t.slot""",
                (label,),
            ).fetchall()
            == party
        )
    db.execute("UPDATE map_object SET kind = 'npc' WHERE name_fr = 'Jessie et James'")
    assert len(validate_team_battles(db)) == 4


def test_yellow_fixed_rival_parties(db: sqlite3.Connection) -> None:
    expected = {
        "oaks-lab": [("eevee", 5)],
        "route-22": [("spearow", 9), ("eevee", 8)],
        "cerulean-city": [("spearow", 18), ("sandshrew", 15), ("rattata", 15), ("eevee", 17)],
        "ss-anne-2f": [("spearow", 19), ("rattata", 16), ("sandshrew", 18), ("eevee", 20)],
    }
    for label, party in expected.items():
        rows = db.execute(
            """SELECT p.identifier, t.level FROM trainer_pokemon t
               JOIN pokemon p ON p.id = t.pokemon_id JOIN map_object o ON o.id = t.map_object_id
               JOIN map m ON m.id = o.map_id JOIN version_group vg ON vg.id = m.version_group_id
               WHERE vg.identifier = 'yellow' AND m.identifier = ? AND o.sprite = 'blue' ORDER BY t.slot""",
            (label,),
        ).fetchall()
        assert rows == party


@pytest.mark.pipeline
@pytest.mark.parametrize("game", [RUBY_SAPPHIRE, EMERALD])
def test_team_trainers_have_matching_graphics(game: Game) -> None:
    repo = Gen3PretRepo(pret_dir(Path(__file__).parents[1] / ".cache", game.pret_repo), game.pret_versions)
    for version, _ in game.pret_versions:
        reader = repo.offers[version]
        for current in repo.maps.values():
            graphics = team_graphics(current, reader.scripts) if repo.ruby else {}
            for index, event in enumerate(current.objects, 1):
                result = reader.read(str(event.value("script")))
                result = team_battle(
                    current, index, apply_team_graphics(event, graphics), result, reader, repo.trainers[version]
                )
                if current.label == "Route119_WeatherInstitute_2F" and index == 3:
                    assert result.offers == ()
                if current.label == "Route119_WeatherInstitute_2F" and index == 5:
                    assert [(offer.kind, offer.pokemon) for offer in result.offers] == [
                        ("gift_pokemon", "SPECIES_CASTFORM")
                    ]
                for name in result.trainers:
                    trainer = repo.trainers[version][name]
                    team = next((team for team in ("AQUA", "MAGMA") if team in trainer.trainer_class), None)
                    if team:
                        sprite = str(apply_team_graphics(event, graphics).value("graphics_id"))
                        assert team in sprite or (team, sprite) in {
                            ("AQUA", "OBJ_EVENT_GFX_ARCHIE"),
                            ("MAGMA", "OBJ_EVENT_GFX_MAXIE"),
                        }


@pytest.mark.pipeline
def test_yellow_rocket_scene_parties() -> None:
    repo = PretRepo(pret_dir(Path(__file__).parents[1] / ".cache", "pokeyellow"))
    for label, level in (("MtMoonB2F", 14), ("RocketHideoutB4F", 25), ("PokemonTower7F", 27), ("SilphCo11F", 31)):
        current = next(current for current in repo.maps.values() if current.label == label)
        jessie = next(obj for obj in current.objects if obj.sprite == "SPRITE_JESSIE")
        james = next(obj for obj in current.objects if obj.sprite == "SPRITE_JAMES")
        assert jessie.kind == "trainer" and james.kind == "npc"
        assert jessie.trainer_number is not None
        party = repo.trainer_parties[("ROCKET", jessie.trainer_number)]
        assert len(party) == 3 and {mon.level for mon in party} == {level}


@pytest.mark.pipeline
def test_yellow_scripted_rivals_have_battle_badges() -> None:
    repo = PretRepo(pret_dir(Path(__file__).parents[1] / ".cache", "pokeyellow"))
    fixed = {
        "OaksLab": ("RIVAL1", 1),
        "Route22": ("RIVAL1", 2),
        "CeruleanCity": ("RIVAL1", 3),
        "SSAnne2F": ("RIVAL2", 1),
    }
    for label in ("OaksLab", "CeruleanCity", "ChampionsRoom", "PokemonTower2F", "Route22", "SilphCo7F", "SSAnne2F"):
        current = next(current for current in repo.maps.values() if current.label == label)
        actors = [obj for obj in current.objects if obj.sprite == "SPRITE_BLUE"]
        assert actors and all(obj.kind == "trainer" for obj in actors)
        if label in fixed:
            trainer_class, number = fixed[label]
            assert (actors[0].trainer_class, actors[0].trainer_number) == ("OPP_" + trainer_class, number)
