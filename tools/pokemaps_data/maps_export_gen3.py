"""Export des cartes et personnages GBA vers la base embarquée."""

from __future__ import annotations

from pathlib import Path

from .games import Game
from .maps import GameMapData
from .maps_catalog_gen3 import map_data
from .maps_characters_gen3 import character_rows
from .maps_gen3 import export_gen3_maps
from .maps_layout import read_layout_curation
from .maps_layout_gen3 import Gen3GameMaps
from .pokeapi import PokeApi
from .pret_gen3 import Gen3PretRepo
from .sources import fetch_pokeapi_csv, fetch_pret
from .story_events import read_story_events
from .validate_gen3_characters import validate_character_catalog


def export_game(cache: Path, output: Path, game: Game) -> GameMapData:
    if not (output / "catalog.tsv").is_file():
        export_gen3_maps(cache, output, game)
    root = fetch_pret(cache, game.pret_repo)
    repo = Gen3PretRepo(root, game.pret_versions)
    maps = Gen3GameMaps(repo, game, read_layout_curation())
    data = map_data(output, root, game)
    story = read_story_events()
    data.objects = character_rows(maps, PokeApi(fetch_pokeapi_csv(cache)), story, output)
    validate_character_catalog(output, game)
    data.characters_complete = True
    data.story = story
    return data
