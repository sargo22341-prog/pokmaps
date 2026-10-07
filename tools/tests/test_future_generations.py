"""Données prévues pour les générations suivantes : vides en 1re génération, remplies pour un jeu plus récent.

Les jeux plus récents ne sont pas encore pris en charge (cartes) : on construit seulement leurs tables de Pokémon,
à partir des mêmes CSV PokéAPI, pour vérifier qu'il suffira de les ajouter dans games.py.
"""

import sqlite3

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import Game
from pokemaps_data.pokeapi import PokeApi

PIKACHU, RAICHU, CLEFAIRY = 25, 26, 35


def _builder(api: PokeApi, version_group: str) -> DatabaseBuilder:
    return DatabaseBuilder(api, games=(Game(version_group, "", (), "", ()),))


def test_gen1_has_none_of_the_later_data(db: sqlite3.Connection) -> None:
    for table in (
        "pokemon_item",
        "egg_group",
        "pokemon_egg_group",
        "ability",
        "ability_version_group",
        "pokemon_ability",
    ):
        assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0, table


def test_held_items_of_a_later_game(builder: DatabaseBuilder) -> None:
    ruby_sapphire = _builder(builder.api, "ruby-sapphire")
    rows = [row for row in ruby_sapphire.items.pokemon_item_rows if row[0] == PIKACHU]
    items = {row[0]: row[1] for row in ruby_sapphire.items.item_rows}
    # Pikachu sauvage : Baie Oran (50 %) et Ballon Lumière (5 %), dans Rubis comme dans Saphir.
    assert {(items[item], rarity) for _, _, item, rarity in rows} == {("oran-berry", 50), ("light-ball", 5)}
    assert {version for _, version, _, _ in rows} == {7, 8}


def test_abilities_follow_their_generation(builder: DatabaseBuilder) -> None:
    def abilities(version_group: str, pokemon_id: int) -> list[tuple[int, str, bool]]:
        later = _builder(builder.api, version_group)
        names = {row[0]: row[1] for row in later.abilities.ability_table()}
        return [
            (slot, names[ability], bool(hidden))
            for species, _, slot, ability, hidden in later.abilities.pokemon_ability_rows
            if species == pokemon_id
        ]

    # Mélofée : Joli Sourire en 3e génération, Garde Magik ajouté en 4e, Garde-Ami caché en 5e.
    assert abilities("ruby-sapphire", CLEFAIRY) == [(1, "cute-charm", False)]
    assert abilities("diamond-pearl", CLEFAIRY) == [(1, "cute-charm", False), (2, "magic-guard", False)]
    assert abilities("black-white", CLEFAIRY) == [
        (1, "cute-charm", False),
        (2, "magic-guard", False),
        (3, "friend-guard", True),
    ]
    descriptions = _builder(builder.api, "black-white").abilities.ability_version_group_table()
    assert all(text for _, _, text in descriptions)


def test_egg_groups_from_the_second_generation(builder: DatabaseBuilder) -> None:
    gold_silver = _builder(builder.api, "gold-silver")
    groups = {row[0]: row[2] for row in gold_silver.pokemon.egg_group_table()}
    assert sorted(groups[group] for species, group in gold_silver.pokemon.egg_group_rows if species == RAICHU) == [
        "Féerique",
        "Terrestre",
    ]
    assert builder.pokemon.egg_group_rows == []
