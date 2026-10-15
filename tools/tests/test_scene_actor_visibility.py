"""Les exclusions visuelles sont explicites et justifiées, sans changer les scripts."""

from pathlib import Path

import pytest

from pokemaps_data.character_curation_gen3 import character_key, read_gen3_curation
from pokemaps_data.games import EMERALD, GEN3_GAMES
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.scene_actor_visibility import read_scene_actor_visibility
from pokemaps_data.sources import pret_dir


def test_door_scene_is_explicit_but_permanent_house_actor_is_visible() -> None:
    actors = read_scene_actor_visibility()
    assert ("ruby-sapphire-emerald", "Route104:LOCALID_ROUTE104_RIVAL") in actors
    assert ("ruby-sapphire-emerald", "LittlerootTown_MaysHouse_2F:LOCALID_RIVALS_HOUSE_2F_RIVAL") not in actors


@pytest.mark.parametrize(
    "row",
    [
        "other,Map:1,Scène\n",
        "ruby-sapphire-emerald,Map,Scène\n",
        "ruby-sapphire-emerald,Map:1,\n",
        "ruby-sapphire-emerald,Map:1\n",
        "ruby-sapphire-emerald,Map:1,Scène,extra\n",
        "ruby-sapphire-emerald,Map:1,Scène\nruby-sapphire-emerald,Map:1,Scène\n",
    ],
)
def test_invalid_or_duplicate_exclusion_names_the_file(tmp_path: Path, row: str) -> None:
    path = tmp_path / "scene_actor_visibility.csv"
    path.write_text("family,text,reason\n" + row, encoding="utf-8")
    with pytest.raises(ValueError, match=r"scene_actor_visibility\.csv"):
        read_scene_actor_visibility(path)


@pytest.mark.pipeline
def test_hidden_rival_keeps_all_raw_battle_references(source_cache_ready: None) -> None:
    cache = Path(__file__).resolve().parents[1] / ".cache"
    repo = Gen3PretRepo(pret_dir(cache, "pokeemerald"), EMERALD.pret_versions)
    current = repo.maps["MAP_ROUTE104"]
    index, event = next(
        (index, event)
        for index, event in enumerate(current.objects, 1)
        if dict(event.fields).get("local_id") == "LOCALID_ROUTE104_RIVAL"
    )
    key = character_key(current.label, event, index)
    assert (EMERALD.map_family, key) in read_scene_actor_visibility()
    assert not read_gen3_curation().is_duplicate(EMERALD.map_family, key)
    reader = repo.offers["emerald"]
    original = reader.read_object(event)
    assert original.trainers
    assert reader.read_curated_object(current.label, event, index, EMERALD.map_family).trainers == original.trainers


@pytest.mark.pipeline
def test_every_visual_exclusion_references_an_existing_actor_on_a_door(source_cache_ready: None) -> None:
    hidden = read_scene_actor_visibility()
    found: set[tuple[str, str]] = set()
    cache = Path(__file__).resolve().parents[1] / ".cache"
    for game in GEN3_GAMES:
        repo = Gen3PretRepo(pret_dir(cache, game.pret_repo), game.pret_versions)
        for current in repo.maps.values():
            for index, event in enumerate(current.objects, 1):
                key = (game.map_family, character_key(current.label, event, index))
                if key not in hidden:
                    continue
                assert (event.x, event.y) in {(warp.x, warp.y) for warp in current.warps}, key
                assert str(event.value("flag")) != "0", key
                found.add(key)
    assert found == hidden
