"""Relecture des deux dépôts DS et de l'aperçu Pokémon complet, sans rendu de cartes."""

import re
import sqlite3
from contextlib import closing
from dataclasses import replace

import pytest

from pokemaps_data.builder import SCHEMA, DatabaseBuilder
from pokemaps_data.builder_forms import form_table
from pokemaps_data.encounter_methods_gen4 import check_encounter_taxonomy
from pokemaps_data.games import DIAMOND_PEARL, GAMES_IN_PROGRESS, GEN4_GAMES, PLATINUM, Game
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_evolution_gen4 import compare_ds_evolutions
from pokemaps_data.pret_items_gen4 import ds_item_constants, ds_item_id
from pokemaps_data.pret_species_gen4 import read_ds_species
from pokemaps_data.preview_pokemon_gen4 import ds_move_rows, pokemon_preview_tables, validate_pokemon_preview
from pokemaps_data.validate import _check_obtainable, _obtainable


def test_ds_games_remain_outside_map_generation() -> None:
    assert GEN4_GAMES == (PLATINUM, DIAMOND_PEARL)
    assert all(game not in GAMES_IN_PROGRESS for game in GEN4_GAMES)


def test_species_and_abilities_are_read_in_both_sources(gen4_builder: DatabaseBuilder) -> None:
    b = gen4_builder
    assert len(b.pokemon.pokemon_table()) == 493
    assert len(b.pokemon.pokemon_version_group_rows()) == 986
    for rows in b.ds_species.values():
        assert rows["turtwig"].stats == (55, 68, 64, 45, 55, 31)
        assert rows["clefairy"].abilities == ("cute-charm", "magic-guard")
    assert all(1 <= r[2] <= 2 and r[4] == 0 for r in b.abilities.pokemon_ability_rows)
    assert len(b.pokemon.pokemon_stat_table()) == 493 * 6
    assert len(b.pokemon.egg_group_rows) >= 493 * 2


def test_pearl_differs_only_by_held_items(gen4_builder: DatabaseBuilder) -> None:
    root = gen4_builder.pret_root(DIAMOND_PEARL, "le test Perle")
    diamond = gen4_builder.ds_species[8]
    pearl = read_ds_species(root, "pokediamond", pearl=True)
    assert {s for s in diamond if diamond[s] != pearl[s]} == {
        "electabuzz",
        "magmar",
        "elekid",
        "magby",
        "electivire",
        "magmortar",
    }
    assert all(replace(row, held_items=pearl[s].held_items) == pearl[s] for s, row in diamond.items())
    held = gen4_builder.items.pokemon_item_rows
    electrizer = gen4_builder.items.ids["electirizer"]
    assert (239, 12, electrizer, 50) in held
    assert (239, 13, electrizer, 5) in held


def test_engine_evolutions_and_all_new_requirements(gen4_builder: DatabaseBuilder) -> None:
    compare_ds_evolutions(gen4_builder)
    rows = gen4_builder.pokemon.evolution_rows
    extras = {r[0]: r[1:] for r in gen4_builder.pokemon.evolution_requirement_rows}
    for group in (8, 9):
        by_target = {r[3]: r for r in rows if r[1] == group}
        assert extras[by_target[226][0]][2] == 223  # Babimanta : Rémoraid dans l'équipe.
        assert extras[by_target[462][0]][0] == 10
        assert extras[by_target[470][0]][:4] == (8, None, None, 1)
        assert extras[by_target[471][0]][:4] == (48, None, None, 1)
        assert extras[by_target[475][0]][1] == 2
        assert extras[by_target[478][0]][1] == 1
        assert by_target[461][9] == "night"
        assert by_target[424][10] == 458
        assert by_target[448][8:10] == (220, "day")


def test_pokedexes_and_move_classes_of_both_groups(gen4_builder: DatabaseBuilder) -> None:
    b = gen4_builder
    assert b.pokedex_links == [(8, 1), (8, 5), (9, 1), (9, 6)]
    entries = b.pokedex_entry_table()
    assert {dex: sum(r[0] == dex for r in entries) for dex in (1, 5, 6)} == {1: 493, 5: 151, 6: 210}
    moves = {(r[1], r[0]): r[2:] for r in ds_move_rows(b)}
    for vg in (8, 9):
        assert moves[(vg, 7)] == (75, 15, 100, 10, "physical")  # Poing Feu, spécial avant la DS.
        assert moves[(vg, 247)][-1] == "special"  # Ball'Ombre, physique avant la DS.
    assert "form-change" in {r[3] for r in b.moves.pokemon_move_rows}


@pytest.mark.parametrize("game", GEN4_GAMES)
def test_all_real_item_constants_are_known(game: Game, gen4_builder: DatabaseBuilder) -> None:
    root = gen4_builder.pret_root(game, "les objets DS")
    constants = ds_item_constants(root, game.pret_repo)
    assert len(constants) > 400
    assert all(ds_item_id(gen4_builder, const) > 0 for const in constants)
    if game.pret_repo == "pokeplatinum":
        lines = (root / "generated/items.txt").read_text(encoding="utf-8").splitlines()
        indices = {name: index for index, name in enumerate(lines)}
    else:
        header = (root / "include/constants/items.h").read_text(encoding="utf-8")
        indices = {
            name: int(index) for name, index in re.findall(r"^#define (ITEM_\w+)\s+(\d+)\s*$", header, re.MULTILINE)
        }
    expected = {
        int(r["game_index"]): int(r["item_id"])
        for r in gen4_builder.api.table("item_game_indices")
        if r["generation_id"] == "4"
    }
    assert all(ds_item_id(gen4_builder, const) == expected[indices[const]] for const in constants)


def test_forms_are_versioned_without_fairy_or_mystery(gen4_builder: DatabaseBuilder) -> None:
    rows = form_table(gen4_builder)
    assert not any(r[2] in {"arceus-fairy", "arceus-unknown"} for r in rows)
    assert {r[0] for r in rows if r[2] == "rotom-heat"} == {14}
    assert {r[0] for r in rows if r[2] == "giratina-origin"} == {14}
    assert {r[0] for r in rows if r[2] == "shellos-east"} == {12, 13, 14}


@pytest.mark.parametrize("method", [7, 8, 9, 11, 12])
def test_unclassified_learning_methods_stop_generation(method: int, gen4_builder: DatabaseBuilder) -> None:
    source = gen4_builder
    api = PokeApi(source.api.root)
    row = next(r for r in source.api.table("pokemon_moves") if r["version_group_id"] == "9")
    api._tables["pokemon_moves"] = ({**row, "pokemon_move_method_id": str(method)},)
    builder = DatabaseBuilder(api, GEN4_GAMES, pret_roots=source.pret_roots)
    with pytest.raises(ValueError, match="Méthode d'apprentissage inconnue"):
        _ = builder.moves.pokemon_move_rows


@pytest.mark.parametrize("table", ["encounter_methods", "encounter_condition_values"])
def test_unknown_encounter_taxonomy_stops_generation(table: str, gen4_builder: DatabaseBuilder) -> None:
    source = gen4_builder
    api = PokeApi(source.api.root)
    rows = source.api.table(table)
    api._tables[table] = ({**rows[0], "identifier": "unknown-ds-condition"}, *rows[1:])
    builder = DatabaseBuilder(api, GEN4_GAMES, pret_roots=source.pret_roots)
    with pytest.raises(ValueError, match="DS inconnues"):
        check_encounter_taxonomy(builder)


def test_reduced_database_validates_obtention_and_rejects_a_missing_encounter(gen4_builder: DatabaseBuilder) -> None:
    tables = pokemon_preview_tables(gen4_builder, set())
    with closing(sqlite3.connect(":memory:")) as c:
        c.executescript(SCHEMA.read_text(encoding="utf-8"))
        c.execute("CREATE TABLE ds_move(move_id, version_group_id, power, pp, accuracy, type_id, damage_class)")
        for table, rows in tables.items():
            if rows:
                c.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)
        assert validate_pokemon_preview(c) == []
        assert (
            c.execute("SELECT count(*) FROM encounter WHERE pokemon_id = 487 AND version_id IN (12, 13)").fetchone()[0]
            == 2
        )
        c.execute("DELETE FROM encounter WHERE pokemon_id IN (223, 224, 226)")
        obtainable = _obtainable(c, 4, (8,))
        assert 458 in obtainable
        assert 223 not in obtainable
        assert 226 not in obtainable
        c.execute("DELETE FROM encounter WHERE pokemon_id = 399")
        c.execute("DELETE FROM encounter WHERE pokemon_id = 400")
        assert any("399" in error for error in _check_obtainable(c))
