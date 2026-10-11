"""Talents GBA : données PokéAPI épinglées comparées aux trois moteurs pret."""

import re

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.pret_gen3_source import balanced_bodies, read_text
from pokemaps_data.sources import pret_dir

from .conftest import CACHE


@pytest.mark.parametrize("repo", ["pokeruby", "pokeemerald", "pokefirered"])
def test_abilities_match_the_engine(repo: str, gen3_builder: DatabaseBuilder) -> None:
    root = pret_dir(CACHE, repo)
    filename = "base_stats.h" if repo == "pokeruby" else "species_info.h"
    path = root / "src/data/pokemon" / filename
    # pokeruby conserve ce fichier en Latin-1 ; les deux autres dépôts utilisent UTF-8.
    text = path.read_text(encoding="latin-1") if repo == "pokeruby" else read_text(path)
    blocks = dict(balanced_bodies(text, r"\[(SPECIES_\w+)\]\s*=\s*\{", 512))
    names = {row[0]: row[1] for row in gen3_builder.abilities.ability_table()}
    generated: dict[int, list[str]] = {}
    for species, generation, _, ability, hidden in gen3_builder.abilities.pokemon_ability_rows:
        assert (generation, hidden) == (3, 0)
        generated.setdefault(species, []).append(names[ability])
    # Espèces anciennes, deux talents, talent unique et talents propres à Hoenn.
    species = {35: "CLEFAIRY", 252: "TREECKO", 282: "GARDEVOIR", 292: "SHEDINJA", 386: "DEOXYS"}
    for pokemon, constant in species.items():
        body = blocks[f"SPECIES_{constant}"]
        constants = re.findall(r"ABILITY_(\w+)", body)
        expected = [name.lower().replace("_", "-") for name in constants if name != "NONE"]
        assert generated[pokemon] == expected, (repo, constant)
    assert set(generated) == set(range(1, 387))


def test_all_games_have_french_ability_names_and_descriptions(gen3_builder: DatabaseBuilder) -> None:
    tables = gen3_builder.abilities
    names = {row[0]: row[2] for row in tables.ability_table()}
    assert names[65] == "Engrais"
    assert names[25] == "Garde Mystik"
    assert names[28] == "Synchro"
    assert names[36] == "Calque"
    used = {row[3] for row in tables.pokemon_ability_rows}
    descriptions = tables.ability_version_group_table()
    assert {(ability, group) for ability, group, _ in descriptions} == {
        (ability, group) for ability in used for group in (5, 6, 7)
    }
    # Six talents n'ont pas de description française GBA dans la source épinglée.
    assert {(ability, group) for ability, group, text in descriptions if text is None} == {
        (ability, group) for ability in (2, 5, 16, 31, 46, 53) for group in (5, 6, 7)
    }
    assert all(text == "Augmente attaques PLANTE." for ability, _, text in descriptions if ability == 65)
