"""Lecture des données de base des espèces dans les trois formats pret, sur des sources réduites."""

from pathlib import Path

import pytest

from pokemaps_data.games import CRYSTAL, GAMES, RUBY_SAPPHIRE
from pokemaps_data.pret_species import Breeding, SpeciesProfile, read_species_profiles

_GEN1_DRAGONITE = """\tdb DEX_DRAGONITE ; pokedex id
\tdb  91, 134,  95,  80, 100
\tdb DRAGON, FLYING ; type
\tdb 9 ; catch rate
\tdb 218 ; base exp
\tdb GROWTH_SLOW ; growth rate
"""
_GEN2_MARILL = """\tdb MARILL ; 183
\tdb 190 ; catch rate
\tdb GENDER_F50 ; gender ratio
\tdb 20 ; step cycles to hatch
IF DEF(_GOLD)
\tINCBIN "gfx/pokemon/marill/front_gold.dimensions"
ENDC
\tdb GROWTH_FAST ; growth rate
\tdn EGG_WATER_1, EGG_FAIRY ; egg groups
"""
_GEN3_SPECIES = """// Pok\xe9mon : commentaire Latin-1 de pokeruby.
    [SPECIES_NONE] = {0},
    [SPECIES_RALTS] =
    {
        .catchRate = 235,
        .genderRatio = PERCENT_FEMALE(50),
        .eggCycles = 20,
        .growthRate = GROWTH_SLOW,
        .eggGroup1 = EGG_GROUP_AMORPHOUS,
        .eggGroup2 = EGG_GROUP_AMORPHOUS,
    },
    [SPECIES_MR_MIME] =
    {
        .types = { TYPE_PSYCHIC, TYPE_PSYCHIC },
        .catchRate = 45,
        .genderRatio = MON_GENDERLESS,
        .eggCycles = 25,
        .growthRate = GROWTH_MEDIUM_FAST,
        .eggGroups = { EGG_GROUP_HUMAN_LIKE, EGG_GROUP_HUMAN_LIKE },
    },
    [SPECIES_OLD_UNOWN_B] = OLD_UNOWN_BASE_STATS,
"""


def _asm(root: Path, name: str, text: str) -> Path:
    folder = root / "data/pokemon/base_stats"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.asm").write_text(text, encoding="utf-8")
    return root


def _gen3(root: Path, text: str) -> Path:
    path = root / "src/data/pokemon/base_stats.h"
    path.parent.mkdir(parents=True)
    path.write_bytes(text.encode("latin-1"))
    return root


def test_first_generation_has_capture_and_growth_only(tmp_path: Path) -> None:
    yellow = next(game for game in GAMES if game.version_group == "yellow")
    root = _asm(tmp_path, "dragonite", _GEN1_DRAGONITE)
    assert read_species_profiles(root, yellow) == {"dragonite": SpeciesProfile(9, "slow", None)}


def test_second_generation_adds_gender_and_eggs(tmp_path: Path) -> None:
    root = _asm(tmp_path, "marill", _GEN2_MARILL)
    assert read_species_profiles(root, CRYSTAL) == {
        "marill": SpeciesProfile(190, "fast", Breeding(4, 20, ("water1", "fairy")))
    }


def test_third_generation_reads_both_initializer_styles(tmp_path: Path) -> None:
    root = _gen3(tmp_path, _GEN3_SPECIES)
    assert read_species_profiles(root, RUBY_SAPPHIRE) == {
        "ralts": SpeciesProfile(235, "slow", Breeding(4, 20, ("indeterminate",))),
        "mr-mime": SpeciesProfile(45, "medium", Breeding(-1, 25, ("humanshape",))),
    }


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("\tdb 190 ; catch rate\n", "\tdb 190 ; catch rate\n\tdb 45 ; catch rate\n", "2 lignes « catch rate »"),
        ("GENDER_F50", "GENDER_F40", "valeur pret inconnue : GENDER_F40"),
        ("EGG_FAIRY", "EGG_ALIEN", "valeur pret inconnue : ALIEN"),
        ("EGG_WATER_1, EGG_FAIRY", "EGG_WATER_1", "groupes d'œufs invalides"),
    ],
)
def test_an_unexpected_asm_source_stops_the_build(tmp_path: Path, old: str, new: str, message: str) -> None:
    root = _asm(tmp_path, "marill", _GEN2_MARILL.replace(old, new))
    with pytest.raises(ValueError, match=message):
        read_species_profiles(root, CRYSTAL)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (".eggCycles = 20,", ".eggCycles = 20,\n        .eggCycles = 10,", "2 champs eggCycles"),
        ("PERCENT_FEMALE(50)", "PERCENT_FEMALE(40)", r"valeur pret inconnue : PERCENT_FEMALE\(40\)"),
        (".catchRate = 235,", "#ifdef RUBY\n        .catchRate = 235,\n#endif", "conditionnelle : RALTS"),
        ("[SPECIES_MR_MIME]", "[SPECIES_RALTS]", "espèce répétée"),
    ],
)
def test_an_unexpected_gba_source_stops_the_build(tmp_path: Path, old: str, new: str, message: str) -> None:
    root = _gen3(tmp_path, _GEN3_SPECIES.replace(old, new, 1))
    with pytest.raises(ValueError, match=message):
        read_species_profiles(root, RUBY_SAPPHIRE)
