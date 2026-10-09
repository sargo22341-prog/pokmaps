"""Rejets des tables particulières des remakes sur des sources autonomes réduites."""

from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.games import FIRERED_LEAFGREEN
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_maps import Gen3Layout, Gen3Map
from pokemaps_data.pret_remake_encounters import roaming_starters, unown_chambers


def _room(index: int) -> Gen3Map:
    names = ("MONEAN", "LIPTOO", "WEEPTH", "DILFORD", "SCUFIB", "RIXY", "VIAPOIS")
    const = f"MAP_SEVEN_ISLAND_TANOBY_RUINS_{names[index]}_CHAMBER"
    layout = Gen3Layout("LAYOUT_TEST", 1, 1, "Primary", "Secondary", (0,), 1, 1, (0,))
    return Gen3Map(
        const,
        names[index],
        index,
        2,
        index,
        layout,
        "MAP_TYPE_CAVE",
        "MAPSEC_TANOBY_RUINS",
        (),
        (),
        (),
        (),
        (),
        None,
        None,
        (),
    )


@pytest.fixture
def letters_repo(tmp_path: Path) -> Gen3PretRepo:
    rows = [list(range(12)), list(range(12, 24)), [24, 25, 26, 27] * 3, *([[0] * 12] * 4)]
    body = ",\n".join("{" + ", ".join(map(str, row)) + "}" for row in rows)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/wild_encounter.c").write_text(
        "static const u8 sUnownLetterSlots[][LAND_WILD_COUNT] = {\n" + body + "\n};", encoding="utf-8"
    )
    repo = Gen3PretRepo(tmp_path, FIRERED_LEAFGREEN.pret_versions)
    repo.maps = {room.const: room for room in (_room(index) for index in range(7))}
    return repo


def test_reduced_tanoby_table_preserves_slot_letters(letters_repo: Gen3PretRepo) -> None:
    rooms = unown_chambers(letters_repo)
    assert rooms[0].letters == tuple(range(12))
    assert rooms[1].letters == tuple(range(12, 24))
    assert rooms[2].letters == (24, 25, 26, 27) * 3


@pytest.mark.parametrize("problem", ("count", "letter", "expression", "coverage", "order", "group", "map"))
def test_tanoby_rejects_invalid_letters_and_map_order(letters_repo: Gen3PretRepo, problem: str) -> None:
    path = letters_repo.root / "src/wild_encounter.c"
    text = path.read_text(encoding="utf-8")
    match problem:
        case "count":
            text = text.replace("0, 1,", "1,", 1)
        case "letter":
            text = text.replace("0, 1,", "28, 1,", 1)
        case "expression":
            text = text.replace("0, 1,", "UNKNOWN, 1,", 1)
        case "coverage":
            text = text.replace("27", "26")
        case "order" | "group":
            const = _room(1).const
            room = letters_repo.maps[const]
            letters_repo.maps[const] = replace(room, group_index=20) if problem == "order" else replace(room, group=3)
        case "map":
            letters_repo.maps.pop(_room(1).const)
        case _:
            raise AssertionError(problem)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=r"wild_encounter\.c"):
        unown_chambers(letters_repo)


@pytest.mark.parametrize("problem", ("none", "starter", "species", "level"))
def test_roaming_rejects_unknown_starters_species_and_level(tmp_path: Path, problem: str) -> None:
    text = "\n".join(
        [
            "switch (GetStarterSpecies())\\",
            "{\\",
            "default:\\",
            "a = SPECIES_RAIKOU;\\",
            "break;\\",
            "case SPECIES_BULBASAUR:\\",
            "a = SPECIES_ENTEI;\\",
            "break;\\",
            "case SPECIES_CHARMANDER:\\",
            "a = SPECIES_SUICUNE;\\",
            "break;\\",
            "}\\",
            "a;\\",
            "CreateMon(mon, species, 50, USE_RANDOM_IVS);",
        ]
    )
    replacements = {
        "none": ("GetStarterSpecies", "Other"),
        "starter": ("BULBASAUR", "PIKACHU"),
        "species": ("RAIKOU", "PIKACHU"),
        "level": ("50", "40"),
    }
    before, after = replacements[problem]
    (tmp_path / "src").mkdir()
    (tmp_path / "src/roamer.c").write_text(text.replace(before, after), encoding="utf-8")
    repo = Gen3PretRepo(tmp_path, FIRERED_LEAFGREEN.pret_versions)
    with pytest.raises(ValueError, match=r"roamer\.c"):
        roaming_starters(repo, "firered")
