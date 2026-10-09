"""Particularités des rencontres des remakes, lues dans le moteur Rouge Feu/Vert Feuille."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


@dataclass(frozen=True)
class UnownChamber:
    map_const: str
    letters: tuple[int, ...]


def unown_chambers(repo: Gen3PretRepo) -> tuple[UnownChamber, ...]:
    path = repo.root / "src/wild_encounter.c"
    text = read_text(path)
    match = re.search(r"sUnownLetterSlots\[\]\[LAND_WILD_COUNT\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not match:
        raise ValueError(f"{path} : table des lettres de Zarbi absente")
    body = re.sub(r"//[^\n]*", "", match[1])
    rows = re.findall(r"\{([^{}]+)\}", body)
    if len(rows) != 7 or re.sub(r"\{[^{}]+\}|[\s,]", "", body):
        raise ValueError(f"{path} : sept chambres de Zarbi attendues")
    maps = sorted(
        (
            current
            for current in repo.maps.values()
            if current.const.startswith("MAP_SEVEN_ISLAND_TANOBY_RUINS_") and current.const.endswith("_CHAMBER")
        ),
        key=lambda current: current.group_index,
    )
    if len(maps) != 7 or len({current.group for current in maps}) != 1:
        raise ValueError(f"{path} : cartes des chambres de Zarbi incohérentes")
    start = maps[0].group_index
    if maps[0].const != "MAP_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER" or [
        current.group_index for current in maps
    ] != list(range(start, start + 7)):
        raise ValueError(f"{path} : ordre des chambres de Zarbi inconnu")
    result = []
    for current, row in zip(maps, rows, strict=True):
        values = row.replace(" ", "").strip().split(",")
        if len(values) != 12 or any(not re.fullmatch(r"\s*\d+\s*", value) for value in values):
            raise ValueError(f"{path} : {current.const} : douze lettres attendues")
        letters = tuple(int(value) for value in values)
        if any(not 0 <= letter < 28 for letter in letters):
            raise ValueError(f"{path} : {current.const} : lettre de Zarbi invalide")
        result.append(UnownChamber(current.const, letters))
    if {letter for chamber in result for letter in chamber.letters} != set(range(28)):
        raise ValueError(f"{path} : les 28 formes de Zarbi ne sont pas couvertes")
    return tuple(result)


def roaming_starters(repo: Gen3PretRepo, version: str) -> dict[str, str]:
    text = repo.source_text("src/roamer.c", version)
    match = re.search(r"switch\s*\(GetStarterSpecies\(\)\)(.*?)\n\s*a;", text, re.S)
    if not match:
        raise ValueError(f"{repo.root}/src/roamer.c : choix de l'errant absent")
    cases = re.findall(r"(default|case SPECIES_\w+):\\\s*a = SPECIES_(\w+);", match[1])
    if len(cases) != 3 or {case for case, _ in cases} != {
        "default",
        "case SPECIES_BULBASAUR",
        "case SPECIES_CHARMANDER",
    }:
        raise ValueError(f"{repo.root}/src/roamer.c : choix de starter inconnu")
    starters = {"default": "squirtle", "case SPECIES_BULBASAUR": "bulbasaur", "case SPECIES_CHARMANDER": "charmander"}
    result = {species.lower(): starters[case] for case, species in cases}
    if set(result) != {"raikou", "entei", "suicune"} or not re.search(r"CreateMon\(mon, species, 50,", text):
        raise ValueError(f"{repo.root}/src/roamer.c : espèces ou niveau des errants inconnus")
    return result
