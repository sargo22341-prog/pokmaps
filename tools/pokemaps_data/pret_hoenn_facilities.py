"""Séries sauvages non capturables de la Pyramide et du Reptile de Combat."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .pret_gen3_source import read_json, read_text
from .pret_identifiers import species_identifier

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


@dataclass(frozen=True)
class FacilityMon:
    species: str
    level_parameter: int
    moves: tuple[str, ...]


@dataclass(frozen=True)
class FacilitySeries:
    facility: str
    mode: str
    series: int
    pokemon: tuple[FacilityMon, ...]


def facility_series(repo: Gen3PretRepo) -> tuple[FacilitySeries, ...]:
    if repo.ruby or repo.remake:
        return ()
    result = []
    for mode, prefix, filename in (
        ("level-50", "sLevel50", "battle_pyramid_level_50_wild_mons.h"),
        ("open-level", "sOpenLevel", "battle_pyramid_open_level_wild_mons.h"),
    ):
        path = repo.root / "src/data/battle_frontier" / filename
        result.extend(_read_series(path, prefix + r"WildMons_Round", "pyramid", mode, 20, 8))
    path = repo.root / "src/battle_pike.c"
    for mode, prefix in (("level-50", "sLvl50_Mons"), ("open-level", "sLvlOpen_Mons")):
        result.extend(_read_series(path, prefix, "pike", mode, 4, 3))
    return tuple(result)


def _read_series(
    path: Path, prefix: str, facility: str, mode: str, count: int, slots: int
) -> tuple[FacilitySeries, ...]:
    text = read_text(path)
    tables = re.findall(prefix + r"(\d+)\[\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if [int(number) for number, _ in tables] != list(range(1, count + 1)):
        raise ValueError(f"{path} : séries de {facility} absentes ou hors ordre")
    return tuple(
        FacilitySeries(facility, mode, int(number), _read_mons(body, path, facility, slots)) for number, body in tables
    )


def _read_mons(body: str, path: Path, facility: str, slots: int) -> tuple[FacilityMon, ...]:
    parameter = "lvl" if facility == "pyramid" else "levelDelta"
    ability = r"\.abilityNum\s*=\s*(?:ABILITY_RANDOM|[01]),\s*" if facility == "pyramid" else ""
    pattern = (
        r"\{\s*\.species\s*=\s*SPECIES_(\w+),\s*\."
        + parameter
        + r"\s*=\s*(\d+),\s*"
        + ability
        + r"\.moves\s*=\s*\{([^{}]+)\}\s*\}"
    )
    matches = re.findall(pattern, body, re.S)
    if len(matches) != slots or re.sub(pattern, "", body, flags=re.S).strip(" \r\n\t,"):
        raise ValueError(f"{path} : emplacements de {facility} invalides")
    result = []
    for species, value, moves in matches:
        level = int(value)
        tokens = tuple(move.strip() for move in moves.split(","))
        if not 0 <= level <= 100 or len(tokens) != 4 or any(not re.fullmatch(r"MOVE_\w+", move) for move in tokens):
            raise ValueError(f"{path} : niveau ou attaques invalides pour {species}")
        result.append(FacilityMon(species_identifier(species), level, tokens))
    return tuple(result)


def write_facility_series(repo: Gen3PretRepo, output: Path) -> None:
    series = facility_series(repo)
    if not series:
        return
    data = {
        "note": "Pokémon non capturables ; assemblages aléatoires non simulés.",
        "level_rules": {
            "pyramid-level-50": "Paramètre de niveau ± 5 ; vingt séries de sept étages, puis répétition.",
            "pyramid-open-level": "Niveau de référence de l'équipe moins le paramètre, puis ± 5.",
            "pike-level-50": "50 moins le paramètre ; séries selon les seuils de 20, 40 et 60 passages.",
            "pike-open-level": "Niveau maximal de l'équipe moins le paramètre, avec un minimum de 60.",
        },
        "series": [asdict(row) for row in series],
    }
    (output / "facility_encounters.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def validate_facility_series(output: Path) -> None:
    data = read_json(output / "facility_encounters.json")
    rows = data.get("series", [])
    expected = {
        (facility, mode, number)
        for facility, count in (("pyramid", 20), ("pike", 4))
        for mode in ("level-50", "open-level")
        for number in range(1, count + 1)
    }
    keys = [(row["facility"], row["mode"], row["series"]) for row in rows]
    if len(keys) != len(expected) or set(keys) != expected or not data.get("note"):
        raise ValueError(f"{output} : séries de combat incohérentes")
    for row in rows:
        if len(row["pokemon"]) != (8 if row["facility"] == "pyramid" else 3):
            raise ValueError(f"{output} : emplacements de combat absents")
        for mon in row["pokemon"]:
            if not re.fullmatch(r"[a-z0-9-]+", mon["species"]) or not 0 <= mon["level_parameter"] <= 100:
                raise ValueError(f"{output} : Pokémon de combat invalide : {mon}")
            if len(mon["moves"]) != 4 or any(not re.fullmatch(r"MOVE_\w+", move) for move in mon["moves"]):
                raise ValueError(f"{output} : attaques de combat invalides : {mon}")
