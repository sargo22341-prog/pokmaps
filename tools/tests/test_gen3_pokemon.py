"""Données Pokémon des jeux de la 3e génération (PokéAPI et règles du moteur lues dans pret), sans cartes."""

import sqlite3
from collections import defaultdict
from pathlib import Path

import pytest

from pokemaps_data.builder import SCHEMA, DatabaseBuilder
from pokemaps_data.games import EXTERNAL_EVENT_NOTE, ONE_OFF_METHODS
from pokemaps_data.pokeapi import PokeApi
from pokemaps_data.pret_gen3_evolution import read_evolution_rules
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import CHECKS, _check_obtainable

from .conftest import CACHE

RUBY_SAPPHIRE, EMERALD, FIRERED_LEAFGREEN = 5, 6, 7
RUBY, SAPPHIRE, FIRERED = 7, 8, 10
NATIONAL, KANTO, HOENN = 1, 2, 4
PIKACHU, EEVEE, ESPEON, UMBREON, PICHU, MARILL, JIRACHI, LUGIA = 25, 133, 196, 197, 172, 183, 385, 249
TREECKO, WURMPLE, SILCOON, CASCOON, GARDEVOIR, NINCADA, NINJASK, SHEDINJA = 252, 265, 266, 268, 282, 290, 291, 292
AZURILL, FEEBAS, MILOTIC = 298, 349, 350
VOLT_TACKLE = 344


def test_each_game_has_its_regional_dex_then_the_national_dex(gen3_builder: DatabaseBuilder) -> None:
    assert gen3_builder.pokedex_links == [
        (RUBY_SAPPHIRE, NATIONAL),
        (RUBY_SAPPHIRE, HOENN),
        (EMERALD, NATIONAL),
        (EMERALD, HOENN),
        (FIRERED_LEAFGREEN, NATIONAL),
        (FIRERED_LEAFGREEN, KANTO),
    ]
    sizes = defaultdict(int)
    for pokedex, _, _ in gen3_builder.pokedex_entry_table():
        sizes[pokedex] += 1
    assert sizes == {NATIONAL: 386, KANTO: 151, HOENN: 202}


def test_new_evolution_conditions(gen3_builder: DatabaseBuilder) -> None:
    rows = {(row[1], row[2], row[3]): row[4:] for row in gen3_builder.pokemon.evolution_rows}
    # (déclencheur, niveau, …, beauté, Attaque comparée à la Défense, probabilité selon la personnalité)
    assert rows[(EMERALD, NINCADA, NINJASK)][:2] == ("level-up", 20)
    assert rows[(EMERALD, NINCADA, SHEDINJA)] == ("shed", *[None] * 10)
    assert rows[(EMERALD, FEEBAS, MILOTIC)][0] == "level-up"
    assert rows[(EMERALD, FEEBAS, MILOTIC)][8] == 170
    for cocoon in (SILCOON, CASCOON):
        assert rows[(RUBY_SAPPHIRE, WURMPLE, cocoon)][1] == 7
        assert rows[(RUBY_SAPPHIRE, WURMPLE, cocoon)][10] == 50


def test_engine_rules_of_each_game(gen3_builder: DatabaseBuilder) -> None:
    rows = {(row[1], row[2], row[3]): row[4:] for row in gen3_builder.pokemon.evolution_rows}
    # PokéAPI donne 160 ; le moteur de la 3e génération demande 220, comme celui de la 2e.
    for group in (RUBY_SAPPHIRE, EMERALD, FIRERED_LEAFGREEN):
        assert rows[(group, AZURILL, MARILL)][4] == 220
    assert rows[(EMERALD, EEVEE, ESPEON)][4:6] == (220, "day")
    assert rows[(EMERALD, EEVEE, UMBREON)][4:6] == (220, "night")
    # Rouge Feu et Vert Feuille n'ont pas d'horloge : Évoli n'y devient ni Mentali ni Noctali.
    assert (FIRERED_LEAFGREEN, EEVEE, ESPEON) not in rows
    assert (FIRERED_LEAFGREEN, EEVEE, UMBREON) not in rows


@pytest.mark.parametrize(("repo", "time_of_day"), [("pokeruby", True), ("pokeemerald", True), ("pokefirered", False)])
def test_evolution_rules_are_read_in_pret(repo: str, time_of_day: bool, source_cache_ready: None) -> None:
    rules = read_evolution_rules(pret_dir(CACHE, repo), repo)
    assert (rules.happiness, rules.time_of_day) == (220, time_of_day)


def test_abilities_of_hoenn_species(gen3_builder: DatabaseBuilder) -> None:
    names = {row[0]: row[1] for row in gen3_builder.abilities.ability_table()}
    abilities = defaultdict(list)
    for species, generation, slot, ability, hidden in gen3_builder.abilities.pokemon_ability_rows:
        assert (generation, hidden) == (3, 0)
        abilities[species].append((slot, names[ability]))
    assert abilities[TREECKO] == [(1, "overgrow")]
    assert abilities[GARDEVOIR] == [(1, "synchronize"), (2, "trace")]
    assert abilities[SHEDINJA] == [(1, "wonder-guard")]


def test_held_items_of_each_version(gen3_builder: DatabaseBuilder) -> None:
    items = {row[0]: row[1] for row in gen3_builder.items.item_rows}
    rows = [row for row in gen3_builder.items.pokemon_item_rows if row[0] == PIKACHU]
    # Pikachu sauvage : Baie Oran (50 %) et Ballon Lumière (5 %) dans Rubis, Saphir et Émeraude ; rien dans Rouge Feu
    # et Vert Feuille (itemCommon et itemRare à ITEM_NONE dans pokefirered).
    assert {(items[item], rarity) for _, _, item, rarity in rows} == {("oran-berry", 50), ("light-ball", 5)}
    assert {version for _, version, _, _ in rows} == {7, 8, 9}


def test_learn_methods_are_classified(gen3_builder: DatabaseBuilder) -> None:
    methods = {row[3] for row in gen3_builder.moves.pokemon_move_rows}
    assert methods == {"level-up", "machine", "egg", "tutor", "light-ball-egg"}
    assert [row for row in gen3_builder.moves.pokemon_move_rows if row[3] == "light-ball-egg"] == [
        (PICHU, EMERALD, VOLT_TACKLE, "light-ball-egg", 0)
    ]


def test_an_unknown_learn_method_stops_the_build(gen3_builder: DatabaseBuilder) -> None:
    methods = tuple(
        {**row, "identifier": "xd-shadow"} if row["identifier"] == "tutor" else row
        for row in gen3_builder.api.table("pokemon_move_methods")
    )
    api = _ApiWith(gen3_builder.api.root, "pokemon_move_methods", methods)
    later = DatabaseBuilder(api, gen3_builder.games, pret_roots=gen3_builder.pret_roots)
    with pytest.raises(ValueError, match="Méthode d'apprentissage inconnue : xd-shadow"):
        _ = later.moves.pokemon_move_rows


def test_an_unknown_evolution_condition_stops_the_build(gen3_builder: DatabaseBuilder) -> None:
    rows = tuple(
        {**row, "needs_overworld_rain": "1"} if row["evolved_species_id"] == str(MILOTIC) else row
        for row in gen3_builder.api.table("pokemon_evolution")
    )
    api = _ApiWith(gen3_builder.api.root, "pokemon_evolution", rows)
    later = DatabaseBuilder(api, gen3_builder.games, pret_roots=gen3_builder.pret_roots)
    with pytest.raises(ValueError, match="needs_overworld_rain"):
        _ = later.pokemon.evolution_rows


def test_one_off_and_external_event_encounters(gen3_builder: DatabaseBuilder) -> None:
    methods = gen3_builder.encounters.method_identifiers
    groups = gen3_builder.encounters.encounter_groups
    totals: dict[tuple[int, int, int], float] = defaultdict(float)
    for group in groups:
        assert (group.chance is None) == (methods[group.method_id] in ONE_OFF_METHODS)
        if group.chance is not None:
            totals[(group.version_id, group.location_area_id, group.method_id)] += group.chance
    assert {round(total, 6) for total in totals.values()} == {100}
    feebas = [group for group in groups if methods[group.method_id] == "feebas-tile-fishing"]
    assert {(group.pokemon_id, group.chance) for group in feebas} == {(FEEBAS, None)}
    jirachi = {methods[group.method_id]: group.notes for group in groups if group.pokemon_id == JIRACHI}
    assert jirachi["pokemon-channel-pal"] == [EXTERNAL_EVENT_NOTE]
    lugia = [group.notes for group in groups if group.pokemon_id == LUGIA]
    assert lugia and all(notes == [EXTERNAL_EVENT_NOTE] for notes in lugia)
    names = {row[1]: row[2] for row in gen3_builder.encounters.encounter_method_table()}
    assert names["feebas-tile-fishing"] == "En pêchant sur une case à Barpau"
    assert gen3_builder.items.name_of("vs-seeker") == "Cherche VS"


def test_every_pokemon_of_both_dexes_can_be_obtained(gen3_builder: DatabaseBuilder, tmp_path: Path) -> None:
    connection = _pokemon_database(gen3_builder, tmp_path / "gen3.db")
    try:
        assert _check_obtainable(connection) == []
        for description, query in CHECKS:
            if "Pokédex" in description:
                assert connection.execute(query).fetchall() == [], description
    finally:
        connection.close()


def _pokemon_database(builder: DatabaseBuilder, path: Path) -> sqlite3.Connection:
    """Base réduite aux tables que lit le contrôle d'obtention (les effets des attaques ne sont pas encore lus)."""
    encounters, _ = builder.encounters.encounter_tables()
    tables = {
        "version_group": builder.version_group_table(),
        "version": builder.version_table(),
        "pokedex": builder.pokedex_table(),
        "version_group_pokedex": builder.pokedex_links,
        "pokedex_entry": builder.pokedex_entry_table(),
        "pokemon": builder.pokemon.pokemon_table(),
        "location": builder.locations.location_rows(builder.encounters.used_areas),
        "location_area": builder.locations.location_area_table(builder.encounters.used_areas),
        "encounter_method": builder.encounters.encounter_method_table(),
        "encounter": encounters,
        "evolution": builder.pokemon.evolution_rows,
        "egg_group": builder.pokemon.egg_group_table(),
        "pokemon_egg_group": builder.pokemon.egg_group_rows,
    }
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    for table, rows in tables.items():
        connection.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(rows[0]))})", rows)
    return connection


class _ApiWith(PokeApi):
    """CSV PokéAPI dont une table est remplacée."""

    def __init__(self, root: Path, name: str, rows: tuple[dict[str, str], ...]) -> None:
        super().__init__(root)
        self._replaced, self._rows = name, rows

    def table(self, name: str) -> tuple[dict[str, str], ...]:
        return self._rows if name == self._replaced else super().table(name)
