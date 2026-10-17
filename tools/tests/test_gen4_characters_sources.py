"""Dresseurs, combats, revanches, objets et Pokédex National lus dans les deux dépôts DS épinglés (tests
`pipeline`)."""

from collections import defaultdict
from functools import cache
from pathlib import Path

import pytest

from pokemaps_data.games import DIAMOND_PEARL, PLATINUM, Game
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_flow_chains import Condition
from pokemaps_data.pret_gen4_source import read_text
from pokemaps_data.preview_characters_gen4 import CharacterCatalog, character_catalog, unbound_trainers
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"
TURTWIG, CHIMCHAR, PIPLUP = 387, 390, 393
# SystemVars_GetRivalStarter (Platine) et sub_0205F398 (Diamant/Perle) : le rival prend le Pokémon de départ
# qui a l'avantage sur celui du joueur ; chaque lignée compte trois espèces consécutives.
RIVAL_STARTER = {TURTWIG: CHIMCHAR, CHIMCHAR: PIPLUP, PIPLUP: TURTWIG}
RIVAL_CLASSES = {"platinum": "TRAINER_CLASS_RIVAL", "diamond-pearl": "TRAINER_CLASS_PKMN_TRAINER_BARRY"}
STARTER_NAMES = {"TURTWIG": TURTWIG, "CHIMCHAR": CHIMCHAR, "PIPLUP": PIPLUP}


@cache
def loaded(game: Game) -> tuple[Gen4PretRepo, CharacterCatalog]:
    repo = Gen4PretRepo(pret_dir(CACHE, game.pret_repo), game.pret_versions)
    return repo, character_catalog(repo, game)


@pytest.fixture(scope="module", params=[PLATINUM, DIAMOND_PEARL], ids=lambda game: game.version_group)
def ds(request: pytest.FixtureRequest, source_cache_ready: None) -> tuple[Gen4PretRepo, CharacterCatalog]:
    return loaded(request.param)


def test_rival_battles_follow_the_player_starter(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    repo, catalog = ds
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    rival_class = RIVAL_CLASSES[catalog.version_group]
    starters_by_file: dict[int, set[int]] = defaultdict(set)
    for battle in catalog.script_battles:
        for variant in battle.variants:
            rival = [trainers[i] for i in variant.opponents if trainers[i].trainer_class == rival_class]
            if not rival or battle.kind == "tag":
                continue
            assert variant.player_starter in RIVAL_STARTER, battle.step
            starters_by_file[battle.script_file].add(variant.player_starter)
            line = RIVAL_STARTER[variant.player_starter]
            species = {mon.species for mon in rival[0].party}
            assert any(_species(repo, name) in range(line, line + 3) for name in species), battle.step
            if repo.platinum and rival[0].const:
                assert STARTER_NAMES[rival[0].const.rsplit("_", 1)[1]] == variant.player_starter
    # Platine : Route 201 (premier combat), Route 203, Porte de la Route 209, Joliberges, Verchamps, Ligue, Aire de
    # Survie ; Diamant/Perle n'a ni le premier combat contre le rival ni l'Aire de Survie avec lui.
    assert len(starters_by_file) == (7 if repo.platinum else 6)
    assert all(starters == set(RIVAL_STARTER) for starters in starters_by_file.values())
    source = read_text(repo.root / ("src/system_vars.c" if repo.platinum else "arm9/asm/unk_0205F314.s"))
    assert ("rivalStarter = SPECIES_CHIMCHAR" in source) if repo.platinum else ("0x00000183" in source)


def _species(repo: Gen4PretRepo, name: str) -> int:
    if repo.platinum:
        return repo.constants[name]
    rows = read_text(repo.root / "include/constants/species.h")
    return int(rows.split(f"#define {name} ")[1].split()[0], 0)


def test_tag_partners_depend_on_starter_and_gender(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    _, catalog = ds
    tags = [battle for battle in catalog.script_battles if battle.kind == "tag"]
    assert len(tags) == (4 if catalog.version_group == "platinum" else 3)
    for battle in tags:
        partners = {variant.partner for variant in battle.variants}
        choices = {(variant.player_starter, variant.player_gender) for variant in battle.variants}
        assert len(partners) == len(battle.variants) == len(choices) and None not in partners
        assert {starter for starter, _ in choices} == set(RIVAL_STARTER)
    assert len(catalog.follower_partners) == 5


def test_survival_area_rival_depends_on_league_victories(source_cache_ready: None) -> None:
    _, catalog = loaded(PLATINUM)
    files = {index for index, places in catalog.script_headers.items() if "MAP_HEADER_SURVIVAL_AREA" in places}
    area = [battle for battle in catalog.script_battles if battle.script_file in files]
    conditions = {c for battle in area for c in battle.conditions if c.subject == "GetLeagueVictories"}
    assert conditions == {Condition("GetLeagueVictories", "<", 20), Condition("GetLeagueVictories", ">=", 20)}


def test_vs_seeker_tables_and_unlocks(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    _, catalog = ds
    assert len(catalog.vs_seeker.series) == 240
    assert all(sites for sites in catalog.vs_seeker_unlocks)
    other = loaded(DIAMOND_PEARL if catalog.version_group == "platinum" else PLATINUM)[1]
    # Même numéro de drapeau pour chaque niveau dans les deux jeux, lu séparément.
    assert catalog.vs_seeker.unlock_flags == other.vs_seeker.unlock_flags == (2431, 2432, 2433, 2434, 2435)


def test_items_and_hidden_coins(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    _, catalog = ds
    kinds = defaultdict(int)
    for item in catalog.items:
        kinds[item.kind] += 1
        assert item.quantity >= 1 and item.item.startswith("ITEM_")
    expected = {"platinum": (328, 262), "diamond-pearl": (260, 241)}[catalog.version_group]
    assert (kinds["item"], kinds["hidden_item"]) == expected
    assert all(730 <= item.flag < 730 + 800 for item in catalog.items if item.kind == "hidden_item")


def test_national_dex_unlock(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    _, catalog = ds
    unlock = catalog.national_dex
    if catalog.version_group == "platinum":
        assert (unlock.headers, unlock.seen_required, unlock.excluded) == (
            ("MAP_HEADER_SANDGEM_TOWN_POKEMON_RESEARCH_LAB",),
            210,
            (),
        )
    else:
        assert (unlock.headers, unlock.seen_required, unlock.excluded) == (
            ("MAP_SANDGEM_ROWANS_LAB",),
            150,
            ("SPECIES_MANAPHY",),
        )
    assert len(unlock.paths) == 2
    for path in unlock.paths:
        assert Condition("flag:2490", "=", 1) in path  # première visite de Vestigion (FLAG_FIRST_ARRIVAL_ETERNA_CITY)
        assert Condition(unlock.check, "=", 1) in path


def test_unbound_trainers_are_placeholders_or_engine_battles(ds: tuple[Gen4PretRepo, CharacterCatalog]) -> None:
    _, catalog = ds
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    unbound = unbound_trainers(catalog)
    placeholders = {"Mickey", "Angelica", "Tara & Tim"}
    rival = RIVAL_CLASSES[catalog.version_group]
    assert not [i for i in unbound if trainers[i].trainer_class == rival and "UNUSED" not in (trainers[i].const or "")]
    assert sum(trainers[i].name in placeholders for i in unbound) >= 120
