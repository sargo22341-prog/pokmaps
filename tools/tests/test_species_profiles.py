"""Données des espèces propres à chaque jeu : celles du jeu (pret), pas les valeurs actuelles de PokéAPI.

Une même espèce est comparée entre les jeux originaux et leurs remakes, et les attributs gardés communs
(sexe, courbe d'expérience, taille, poids) sont confrontés aux sources de chaque jeu.
"""

import re
import sqlite3

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import EMERALD, FIRERED_LEAFGREEN, Game
from pokemaps_data.pret_identifiers import species_identifier
from pokemaps_data.validate import CHECKS

from .test_gen3_pokemon import _ApiWith

RED_BLUE, YELLOW, GOLD_SILVER, CRYSTAL, RUBY_SAPPHIRE, EMERALD_ID, FIRERED_LEAFGREEN_ID = range(1, 8)
PIKACHU, RATICATE, DRAGONAIR, DRAGONITE, MARILL = 25, 20, 148, 149, 183
RALTS, TRAPINCH, KYOGRE, RAYQUAZA = 280, 328, 382, 384
# (espèce, groupe de versions) -> (taux de capture, cycles d'éclosion) relevés dans pret. PokéAPI donne 127 pour
# Rattatac, 45 pour Draco, Dracolosse et Rayquaza, 3 pour Kyogre et 10 cycles pour Marill.
CHANGED_VALUES = {
    (RATICATE, RED_BLUE): (90, None),
    (RATICATE, GOLD_SILVER): (90, 15),
    (RATICATE, FIRERED_LEAFGREEN_ID): (127, 15),
    (DRAGONAIR, RED_BLUE): (45, None),
    (DRAGONAIR, YELLOW): (27, None),
    (DRAGONITE, YELLOW): (9, None),
    (DRAGONITE, FIRERED_LEAFGREEN_ID): (45, 40),
    (MARILL, CRYSTAL): (190, 20),
    (MARILL, EMERALD_ID): (190, 10),
    (KYOGRE, RUBY_SAPPHIRE): (5, 120),
    (RAYQUAZA, EMERALD_ID): (3, 120),
}


def test_the_shipped_database_has_the_values_of_each_game(db: sqlite3.Connection) -> None:
    rows = {
        (pokemon, group): (capture, hatch)
        for pokemon, group, capture, hatch in db.execute("SELECT * FROM pokemon_version_group")
    }
    assert {key: rows[key] for key in CHANGED_VALUES} == CHANGED_VALUES
    groups = db.execute(
        """SELECT peg.pokemon_id, peg.version_group_id, eg.identifier FROM pokemon_egg_group peg
           JOIN egg_group eg ON eg.id = peg.egg_group_id WHERE peg.pokemon_id IN (?, ?, ?)""",
        (PIKACHU, RALTS, TRAPINCH),
    ).fetchall()
    # Tarsal et Kraknoix ne sont Humanoïde ou Draconique qu'après la 3e génération.
    assert {(pokemon, group) for pokemon, vg, group in groups if vg == EMERALD_ID} == {
        (PIKACHU, "ground"),
        (PIKACHU, "fairy"),
        (RALTS, "indeterminate"),
        (TRAPINCH, "bug"),
    }
    assert not [row for row in groups if row[1] in (RED_BLUE, YELLOW)]


def test_the_description_names_the_game_it_comes_from(db: sqlite3.Connection) -> None:
    # PokéAPI n'a aucun texte français des jeux de la base : toutes les descriptions viennent de Pokémon Noir.
    assert db.execute("SELECT DISTINCT description_version_fr FROM pokemon").fetchall() == [("Noir",)]


@pytest.mark.parametrize(
    ("change", "check"),
    [
        ("DELETE FROM pokemon_version_group WHERE pokemon_id = 25 AND version_group_id = 1", "données d'espèce"),
        ("UPDATE pokemon_version_group SET hatch_counter = 10 WHERE version_group_id = 1", "données d'espèce"),
        ("UPDATE pokemon_version_group SET hatch_counter = NULL WHERE version_group_id = 3", "données d'espèce"),
        ("UPDATE pokemon_version_group SET capture_rate = 0 WHERE pokemon_id = 25", "données d'espèce"),
        ("UPDATE pokemon SET description_version_fr = NULL WHERE id = 25", "description du Pokédex"),
        ("INSERT INTO pokemon_egg_group VALUES (25, 1, 5)", "groupe d'œufs incohérent"),
        ("DELETE FROM pokemon_egg_group WHERE pokemon_id = 25 AND version_group_id = 3", "sans groupe d'œufs"),
    ],
)
def test_validation_detects_invalid_game_data(db: sqlite3.Connection, change: str, check: str) -> None:
    (query,) = [query for description, query in CHECKS if check in description]
    assert db.execute(query).fetchall() == []
    db.execute(change)
    assert db.execute(query).fetchall()


@pytest.mark.parametrize(("species", "group"), list(CHANGED_VALUES))
def test_the_build_reads_the_values_of_each_game(builder: DatabaseBuilder, species: int, group: int) -> None:
    rows = {
        (pokemon, vg): (capture, hatch) for pokemon, vg, capture, hatch in builder.pokemon.pokemon_version_group_rows()
    }
    assert rows[(species, group)] == CHANGED_VALUES[(species, group)]


def test_common_attributes_that_differ_in_a_game_stop_the_build(builder: DatabaseBuilder) -> None:
    species = tuple(
        {**row, "gender_rate": "8"} if row["id"] == str(PIKACHU) else row
        for row in builder.api.table("pokemon_species")
    )
    later = DatabaseBuilder(_ApiWith(builder.api.root, "pokemon_species", species), pret_roots=builder.pret_roots)
    with pytest.raises(ValueError, match=f"pour l'espèce {PIKACHU}"):
        later.pokemon.pokemon_table()


@pytest.mark.parametrize("game", [EMERALD, FIRERED_LEAFGREEN], ids=lambda game: game.version_group)
def test_heights_and_weights_are_those_of_the_gba_pokedex(builder: DatabaseBuilder, game: Game) -> None:
    root = builder.pret_roots[game.version_group]
    text = (root / "src/data/pokemon/pokedex_entries.h").read_text(encoding="utf-8")
    entries = re.findall(r"\[NATIONAL_DEX_(\w+)\]\s*=\s*\{[^{}]*?\.height = (\d+),\s*\.weight = (\d+),", text)
    pokedex = {
        species_identifier(name): (int(height), int(weight)) for name, height, weight in entries if name != "NONE"
    }
    database = {
        row[1]: (row[10], row[11])
        for row in builder.pokemon.pokemon_table()
        if int(builder.species[row[0]]["generation_id"]) <= 3
    }
    assert len(pokedex) == len(database) == 386
    assert pokedex == database
