"""Noms français des classes de dresseurs et des personnages DS lus dans les deux dépôts épinglés (tests
`pipeline`)."""

from pathlib import Path

from pokemaps_data.character_names_gen4 import DYNAMIC, dynamic_sprites, sprite_key, sprite_keys, unused_names
from pokemaps_data.games import DIAMOND_PEARL, GEN4_GAMES, PLATINUM
from pokemaps_data.maps_characters_data import read_character_names
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.preview_characters_gen4 import character_catalog
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"


def test_every_class_and_placed_character_has_a_french_name(source_cache_ready: None) -> None:
    names = read_character_names()
    repos = {
        game.version_group: Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions) for game in GEN4_GAMES
    }
    found = {
        group: character_catalog(repo, game, names=names).names
        for (group, repo), game in zip(repos.items(), GEN4_GAMES, strict=True)
    }
    assert unused_names(names, found, repos) == []
    platinum, diamond = found[PLATINUM.version_group], found[DIAMOND_PEARL.version_group]
    # Même constante qu'en 3e génération, autre nom français (Poképédia) : les lignes DS sont propres au dépôt.
    assert names.trainer("TRAINER_CLASS_PICNICKER") != platinum.classes["TRAINER_CLASS_PICNICKER"] == "Pique-Nique"
    assert (
        platinum.classes["TRAINER_CLASS_TOWER_TYCOON"] == diamond.classes["TRAINER_CLASS_TOWER_TYCOON"] == "Aigle Tour"
    )
    assert diamond.classes["TRAINER_CLASS_PKMN_TRAINER_BARRY"] == platinum.classes["TRAINER_CLASS_RIVAL"] == "Rival"
    assert platinum.sprites[151] == diamond.sprites[151] == ("Créhelf", "pokemon")
    assert diamond.sprites[87] == ("Poké Ball", "object")


def test_dynamic_and_unnamed_sprites_get_their_keys(source_cache_ready: None) -> None:
    platinum = Gen4PretRepo(pret_dir(CACHE, PLATINUM.pret_repo), PLATINUM.pret_versions)
    diamond = Gen4PretRepo(pret_dir(CACHE, DIAMOND_PEARL.pret_repo), DIAMOND_PEARL.pret_versions)
    assert dynamic_sprites(platinum) == range(101, 117)
    assert dynamic_sprites(diamond) == range(101, 118)
    pt_keys, dp_keys = sprite_keys(platinum), sprite_keys(diamond)
    assert sprite_key(platinum, pt_keys, dynamic_sprites(platinum), 104) == DYNAMIC
    assert sprite_key(platinum, pt_keys, dynamic_sprites(platinum), 91) == "pokeplatinum:OBJ_EVENT_GFX_MAP_SIGNPOST"
    # Diamant/Perle ne nomme pas les panneaux ; pret y écrit SPRTIE_SUNGLASSES pour le guide de l'arène.
    assert sprite_key(diamond, dp_keys, dynamic_sprites(diamond), 91) == "pokediamond:91"
    assert sprite_key(diamond, dp_keys, dynamic_sprites(diamond), 168) == "pokediamond:SPRTIE_SUNGLASSES"
