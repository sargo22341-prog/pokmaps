"""Données prévues pour les générations suivantes : vides en 1re génération, remplies pour un jeu plus récent.

On construit seulement les tables de Pokémon, à partir des mêmes CSV PokéAPI : celles de Rubis et Saphir (déclarés
dans games.py), et celles de jeux encore absents de games.py, pour vérifier qu'il suffira de les y ajouter.
"""

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import GEN3_GAMES, Game, PretFormat
from pokemaps_data.pokeapi import PokeApi

RAICHU, CLEFAIRY = 26, 35


def _builder(api: PokeApi, version_group: str) -> DatabaseBuilder:
    # Sans cartes ni désassemblage : seules les tables qui ne lisent pas pret sont construites. Un jeu absent de
    # games.py prend un format pret quelconque, qu'aucune de ces tables ne lit.
    declared = {game.version_group: game for game in GEN3_GAMES}
    game = declared.get(version_group) or Game(version_group, "", (), "", (), PretFormat.GEN1, ())
    return DatabaseBuilder(api, games=(game,))


def test_gen1_has_none_of_the_later_data(builder: DatabaseBuilder) -> None:
    gen1 = _builder(builder.api, "red-blue")
    assert gen1.items.pokemon_item_rows == []
    assert gen1.pokemon.egg_group_table() == []
    assert gen1.pokemon.egg_group_rows == []
    assert gen1.abilities.ability_table() == []
    assert gen1.abilities.ability_version_group_table() == []
    assert gen1.abilities.pokemon_ability_rows == []


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
    assert _builder(builder.api, "red-blue").pokemon.egg_group_rows == []
