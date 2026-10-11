"""Couverture des noms français sur les trois dépôts GBA épinglés."""

from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.character_names_gen3 import validate_gen3_names
from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.maps_characters_data import read_character_names
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.sources import pret_dir


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_pinned_names_and_missing_entries(source_cache_ready: None, game: Game) -> None:
    cache = Path(__file__).resolve().parents[1] / ".cache"
    repo = Gen3PretRepo(pret_dir(cache, game.pret_repo), game.pret_versions)
    names = read_character_names()
    validate_gen3_names(repo, game.map_family, names)
    with pytest.raises(ValueError, match=r"trainer_classes\.csv"):
        validate_gen3_names(repo, game.map_family, replace(names, trainers={}))
    with pytest.raises(ValueError, match=r"npc_names\.csv"):
        validate_gen3_names(repo, game.map_family, replace(names, characters={}))
    with pytest.raises(ValueError, match=r"npc_text_names\.csv"):
        validate_gen3_names(repo, game.map_family, replace(names, by_text={}))


def test_curated_scripts_exist_in_their_family(source_cache_ready: None) -> None:
    cache = Path(__file__).resolve().parents[1] / ".cache"
    scripts: dict[str, set[str]] = {}
    for game in GEN3_GAMES:
        repo = Gen3PretRepo(pret_dir(cache, game.pret_repo), game.pret_versions)
        scripts.setdefault(game.map_family, set()).update(
            str(event.value("script")) for current in repo.maps.values() for event in current.objects
        )
    names = read_character_names()
    for key, family in names.text_families.items():
        if family in scripts:
            assert key in scripts[family], key
