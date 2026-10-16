"""Règles sauvages lues dans les deux moteurs DS épinglés, tables par version et comparaison avec PokéAPI
(tests `pipeline`)."""

from collections import Counter
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.builder_wild_gen4 import wild_context
from pokemaps_data.compare_wild_gen4 import Difference, compare_gen4_tables
from pokemaps_data.encounter_methods_gen4 import check_encounter_taxonomy
from pokemaps_data.games import DIAMOND_PEARL, PLATINUM, Game
from pokemaps_data.maps_terrain_gen4 import header_terrain
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_wild import WildContext, wild_tables
from pokemaps_data.pret_gen4_wild_extra import TROPHY_GARDEN
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate_encounters_gen4 import wrong_combinations

CACHE = Path(__file__).resolve().parent.parent / ".cache"
WATER = (60, 30, 5, 4, 1)
ROD = (40, 40, 15, 4, 1)
# Zones de PokéAPI regroupées autrement par le moteur (extra_areas.csv) : leurs tables n'existent que d'un côté.
REGROUPED = ("solaceon-ruins/", "turnback-cave/", "mt-coronet/exterior-", "mt-coronet/north-", "mt-coronet/south-")
# Erreurs de PokéAPI : Pokéradar dans des lieux sans hautes herbes, essaims hors de la liste du moteur.
POKEAPI_RADAR = frozenset(
    {"oreburgh-mine/1f", "oreburgh-mine/b1f", "wayward-cave/1f", *(f"lost-tower/{n}f" for n in "345")}
)
POKEAPI_SWARMS = frozenset(
    {("diamond", "lake-verity/before-galactic-intervention"), ("pearl", "lake-verity/before-galactic-intervention")}
    | {("platinum", "iron-island/b3f")}
)


@pytest.fixture(scope="module", params=[PLATINUM, DIAMOND_PEARL], ids=lambda game: game.version_group)
def ds(request: pytest.FixtureRequest, source_cache_ready: None) -> tuple[Game, Gen4PretRepo, WildContext]:
    game: Game = request.param
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    return game, repo, wild_context(repo)


@pytest.fixture(scope="module")
def contexts(source_cache_ready: None) -> dict[str, WildContext]:
    return {
        game.version_group: wild_context(Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions))
        for game in (PLATINUM, DIAMOND_PEARL)
    }


def test_engine_rules_read_in_c_and_in_assembly_agree(contexts: dict[str, WildContext]) -> None:
    platinum, dp = contexts["platinum"].rules, contexts["diamond-pearl"].rules
    assert platinum.rates == dp.rates
    assert platinum.rates.land == (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1) and platinum.rates.surf == WATER
    assert platinum.rates.rods == (("old-rod", WATER), ("good-rod", ROD), ("super-rod", ROD))
    assert platinum.replacements == dp.replacements
    assert (platinum.replacements.swarm, platinum.replacements.time, platinum.replacements.radar) == (
        (0, 1),
        (2, 3),
        (4, 5, 10, 11),
    )
    assert (platinum.replacements.daily, platinum.replacements.dual_slot) == ((6, 7), (8, 9))
    assert platinum.tiles == dp.tiles and len(platinum.tiles.grass) == 4
    for field in ("slot_rates", "levels", "normal_groups", "munchlax_groups", "model"):
        assert getattr(platinum.honey, field) == getattr(dp.honey, field), field
    assert platinum.honey.normal_groups == (10, 70, 20, 0) and platinum.honey.munchlax_groups == (9, 20, 70, 1)
    assert platinum.honey.slot_rates == (40, 20, 20, 10, 5, 5) and platinum.honey.levels == (5, 15)
    assert platinum.unown_forms == dp.unown_forms and len(platinum.unown_forms) == 8
    assert platinum.feebas[1] == dp.feebas[1] == (10, 20)
    assert len(set(platinum.roamer_headers)) == len(set(dp.roamer_headers)) == 29


def test_rules_that_differ_between_the_games(contexts: dict[str, WildContext]) -> None:
    platinum, dp = contexts["platinum"], contexts["diamond-pearl"]
    assert (len(set(platinum.rules.swarm_headers)), len(set(dp.rules.swarm_headers))) == (22, 28)
    assert platinum.rules.honey.tables == (("platinum", (2, 3, 4)),)
    assert dp.rules.honey.tables == (("diamond", (2, 3, 4)), ("pearl", (5, 6, 7)))
    assert dp.extra[2] != dp.extra[5] and 266 in dp.extra[2] and 268 in dp.extra[5]  # Armulys, Blindalys
    assert platinum.rules.roamers == ((481, 50), (488, 50), (146, 60), (145, 60), (144, 60))
    assert dp.rules.roamers == ((481, 50), (488, 50))
    # Métamorph remplace Porygon au Jardin Trophée de Platine.
    assert 132 in platinum.extra[TROPHY_GARDEN] and 137 in dp.extra[TROPHY_GARDEN]


def test_every_table_totals_100_for_each_combination(ds: tuple[Game, Gen4PretRepo, WildContext]) -> None:
    game, repo, context = ds
    for version, _ in game.pret_versions:
        tables = wild_tables(repo, context, version)
        assert len(tables) == {"platinum": 379, "diamond": 375, "pearl": 375}[version]
        for table in tables:
            rows = [(slot.chance, frozenset(slot.conditions)) for slot in table.slots]
            assert wrong_combinations(rows) == [], (version, repo.headers[table.header].constant, table.method)
            radar = any("radar-on" in slot.conditions for slot in table.slots)
            assert not radar or table.header in context.radar_headers
            swarm = any("swarm-yes" in slot.conditions for slot in table.slots)
            assert not swarm or table.header in context.rules.swarm_headers


def test_radar_and_honey_tree_terrains(ds: tuple[Game, Gen4PretRepo, WildContext]) -> None:
    _, repo, context = ds
    assert len(context.radar_headers) == 46
    names = {repo.headers[index].constant for index in context.radar_headers}
    assert not any("MINE" in name or "GREAT_MARSH" in name or "LOST_TOWER" in name for name in names)
    for index in sorted(set(context.rules.honey.headers)):
        terrain = header_terrain(repo, repo.headers[index], context.rules, frozenset({"honey-tree"}))
        assert len(terrain.cells["tree"]) == 1, repo.headers[index].constant


def test_engine_encounters_enter_the_builder_and_differ_from_pokeapi_only_where_explained(
    gen4_builder: DatabaseBuilder,
) -> None:
    check_encounter_taxonomy(gen4_builder)
    data = gen4_builder.encounters.gen4_wild
    assert {group: len(value.encounters) for group, value in data.items()} == {
        "platinum": 5086,
        "diamond-pearl": 10394,
    }
    assert all(value.feebas == (349, 10, 20) for value in data.values())
    differences = compare_gen4_tables(gen4_builder)
    assert Counter(_explanation(row) for row in differences) == {
        "zone regroupée": 192,
        "Pokémon du jour en probabilité moyenne": 21,
        "Pokéradar de PokéAPI hors des hautes herbes": 6,
        "essaim de PokéAPI hors de la liste du moteur": 3,
    }


def _explanation(row: Difference) -> str:
    if (not row.pokeapi or not row.pret) and row.area.startswith(REGROUPED):
        return "zone regroupée"
    if row.area.startswith("great-marsh/") or row.area == "trophy-garden":
        return "Pokémon du jour en probabilité moyenne"
    if row.area in POKEAPI_RADAR and "radar-on" in row.conditions:
        return "Pokéradar de PokéAPI hors des hautes herbes"
    if (row.version, row.area) in POKEAPI_SWARMS and "swarm-yes" in row.conditions:
        return "essaim de PokéAPI hors de la liste du moteur"
    return f"inexpliqué : {row}"
