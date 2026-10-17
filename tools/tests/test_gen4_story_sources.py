"""Étapes du scénario traduites pour les deux dépôts DS épinglés (tests `pipeline`)."""

from pathlib import Path

from pokemaps_data.games import GEN4_GAMES
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.preview_characters_gen4 import CharacterCatalog, character_catalog
from pokemaps_data.sources import pret_dir
from pokemaps_data.story_events import DS_REPOS, read_story_events

CACHE = Path(__file__).resolve().parent.parent / ".cache"


def _scenario(catalog: CharacterCatalog, prefix: str) -> tuple[tuple[str, ...], ...]:
    found = [paths for label, paths in catalog.scenario.items() if label.startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]


def test_every_ds_condition_is_described_and_every_row_is_used(source_cache_ready: None) -> None:
    story = read_story_events()
    catalogs = {}
    for game in GEN4_GAMES:
        repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
        catalogs[game.version_group] = character_catalog(repo, game, story)
    assert story.unused(set(DS_REPOS)) == []
    platinum, diamond = catalogs["platinum"], catalogs["diamond-pearl"]
    rotom = _scenario(platinum, "fixe MAP_HEADER_OLD_CHATEAU_BACK_MIDDLE_WEST_ROOM")
    assert rotom == (("Avant la capture de Motisma", "Une fois par jour", "La nuit"),)
    assert _scenario(diamond, "fixe MAP_OLD_CHATEAU_2F_ROOM_2") == (
        (
            "Avant la capture de Motisma",
            "Une fois par jour",
            "Après la victoire à la Ligue Pokémon",
            "Après l'obtention du Pokédex National",
            "La nuit",
        ),
    )
    assert _scenario(platinum, "position MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM") == (
        ("Pendant la traversée du Monde Distorsion, avant le combat contre Giratina",),
    )
    for catalog in catalogs.values():
        for path in catalog.scenario["pokedex_national"]:
            assert "Après la première visite de Vestigion" in path
