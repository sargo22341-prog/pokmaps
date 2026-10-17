"""Pokémon fixes lus dans les deux dépôts DS épinglés (tests `pipeline`) : espèces, niveaux, versions, positions."""

from pathlib import Path

import pytest

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM, Game
from pokemaps_data.maps_layout_gen4 import selected_headers
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_fixed import FixedEncounter, FixedPokemon, game_versions, read_fixed_encounters
from pokemaps_data.pret_gen4_flow_chains import Condition
from pokemaps_data.pret_gen4_source import metang_enum
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"
# (lieu, espèce, niveau) de chaque Pokémon fixe, relus dans les scripts de chaque jeu.
PLATINUM_FIXED = {
    ("MAP_HEADER_ACUITY_CAVERN", "UXIE", 50),
    ("MAP_HEADER_VALOR_CAVERN", "AZELF", 50),
    ("MAP_HEADER_SPEAR_PILLAR_DIALGA", "DIALGA", 70),
    ("MAP_HEADER_SPEAR_PILLAR_PALKIA", "PALKIA", 70),
    ("MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM", "GIRATINA", 47),
    ("MAP_HEADER_TURNBACK_CAVE_GIRATINA_ROOM", "GIRATINA", 47),
    ("MAP_HEADER_STARK_MOUNTAIN_ROOM_3", "HEATRAN", 50),
    ("MAP_HEADER_SNOWPOINT_TEMPLE_B5F", "REGIGIGAS", 1),
    ("MAP_HEADER_ROCK_PEAK_RUINS", "REGIROCK", 30),
    ("MAP_HEADER_ICEBERG_RUINS", "REGICE", 30),
    ("MAP_HEADER_IRON_RUINS", "REGISTEEL", 30),
    ("MAP_HEADER_OLD_CHATEAU_BACK_MIDDLE_WEST_ROOM", "ROTOM", 20),
    ("MAP_HEADER_ROUTE_209", "SPIRITOMB", 25),
    ("MAP_HEADER_VALLEY_WINDWORKS_OUTSIDE", "DRIFLOON", 15),
    ("MAP_HEADER_NEWMOON_ISLAND_FOREST", "DARKRAI", 50),
    ("MAP_HEADER_FLOWER_PARADISE", "SHAYMIN", 30),
    ("MAP_HEADER_HALL_OF_ORIGIN", "ARCEUS", 80),
}
DIAMOND_PEARL_FIXED = {
    ("MAP_ACUITY_CAVERN", "UXIE", 50),
    ("MAP_VALOR_CAVERN", "AZELF", 50),
    ("MAP_MOUNT_CORONET_SPEAR_PILLAR", "DIALGA", 47),
    ("MAP_MOUNT_CORONET_SPEAR_PILLAR", "PALKIA", 47),
    ("MAP_TURNBACK_CAVE_GIRATINA_ROOM", "GIRATINA", 70),
    ("MAP_STARK_MOUNTAIN_INTERIOR_3", "HEATRAN", 70),
    ("MAP_SNOWPOINT_TEMPLE_B5F", "REGIGIGAS", 70),
    ("MAP_OLD_CHATEAU_2F_ROOM_2", "ROTOM", 15),
    ("MAP_ROUTE_209", "SPIRITOMB", 25),
    ("MAP_VALLEY_WINDWORKS_EXTERIOR", "DRIFLOON", 22),
    ("MAP_NEWMOON_ISLAND_INTERIOR", "DARKRAI", 40),
    ("MAP_FLOWER_PARADISE", "SHAYMIN", 30),
    ("MAP_HALL_OF_ORIGIN", "ARCEUS", 80),
}


def fixed(game: Game) -> tuple[Gen4PretRepo, tuple[FixedEncounter, ...]]:
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    return repo, read_fixed_encounters(repo, selected_headers(repo))


@pytest.mark.parametrize(
    ("game", "expected"), [(PLATINUM, PLATINUM_FIXED), (DIAMOND_PEARL, DIAMOND_PEARL_FIXED)], ids=["pt", "dp"]
)
def test_each_fixed_pokemon_is_read(source_cache_ready: None, game: Game, expected: set) -> None:
    _, encounters = fixed(game)
    found = {
        (encounter.header, pokemon.species.removeprefix("SPECIES_"), pokemon.level)
        for encounter in encounters
        for pokemon in encounter.pokemon
    }
    assert found == expected
    assert all(encounter.positions for encounter in encounters)


def test_spear_pillar_follows_the_diamond_pearl_version(source_cache_ready: None) -> None:
    repo, encounters = fixed(DIAMOND_PEARL)
    assert game_versions(repo) == {10: "diamond", 11: "pearl"}
    pillar = [encounter for encounter in encounters if encounter.header == "MAP_MOUNT_CORONET_SPEAR_PILLAR"]
    assert len(pillar) == 2  # premier passage et retour après la Ligue, deux déclencheurs
    for encounter in pillar:
        assert encounter.pokemon == (
            FixedPokemon(("diamond",), "SPECIES_DIALGA", 47),
            FixedPokemon(("pearl",), "SPECIES_PALKIA", 47),
        )
        assert [position.kind for position in encounter.positions] == ["trigger"]


def test_origin_giratina_is_placed_by_the_distortion_world_engine(source_cache_ready: None) -> None:
    repo, encounters = fixed(PLATINUM)
    progress = metang_enum(repo.root / "generated/vars_flags.txt")["VAR_DISTORTION_WORLD_PROGRESS"]
    [room] = [encounter for encounter in encounters if encounter.header == "MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM"]
    assert room.battle == "giratina_origin"
    [position] = room.positions
    # DIST_WORLD_PROGRESS_GIRATINA_ARRIVED vaut 13 ; Giratina se tient sur la case (15, 13), une case plus haut.
    assert (position.x, position.z, position.y) == (15, 13, 16 * 4096)
    assert position.conditions == (Condition(f"var:{progress}", "=", 13),)


@pytest.mark.parametrize("game", [PLATINUM, DIAMOND_PEARL], ids=["pt", "dp"])
def test_placed_legendaries_have_a_removal_flag(source_cache_ready: None, game: Game) -> None:
    _, encounters = fixed(game)
    placed = [p for encounter in encounters for p in encounter.positions if p.kind == "object" and p.removal_flag]
    unflagged = {e.header for e in encounters for p in e.positions if p.kind == "object" and not p.removal_flag}
    assert len(placed) == 8
    assert unflagged == ({"MAP_HEADER_DISTORTION_WORLD_GIRATINA_ROOM"} if game is PLATINUM else set())
