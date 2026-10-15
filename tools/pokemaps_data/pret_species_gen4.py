"""Données personnelles DS : chaque variante est lue dans son propre dépôt, sans ROM."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .pret_identifiers import species_identifier

_MAX_JSON_BYTES = 4 * 1024 * 1024
_STATS = ("hp", "attack", "defense", "special_attack", "special_defense", "speed")
_DP_STATS = ("hp", "atk", "def", "spatk", "spdef", "speed")
_SPECIAL_DP = frozenset(
    {"NONE", "EGG", "MANAPHY_EGG", "DEOXYS_ATK", "DEOXYS_DEF", "DEOXYS_SPD", "WORMADAM_SANDY", "WORMADAM_TRASH"}
)


@dataclass(frozen=True)
class DsSpecies:
    identifier: str
    stats: tuple[int, ...]
    types: tuple[str, ...]
    abilities: tuple[str, ...]
    held_items: tuple[str, str]
    capture_rate: int
    gender_rate: int
    hatch_cycles: int
    growth: str
    egg_groups: tuple[str, ...]
    evolutions: tuple[tuple[str, int | str, str], ...]


def read_json(path: Path) -> dict:
    if path.stat().st_size > _MAX_JSON_BYTES:
        raise ValueError(f"{path} : JSON DS trop volumineux")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} : objet JSON attendu")
    return value


def read_ds_species(root: Path, repo: str, *, pearl: bool = False) -> dict[str, DsSpecies]:
    if repo == "pokeplatinum":
        paths = [
            p
            for p in sorted((root / "res/pokemon").glob("*/data.json"))
            if p.parent.name not in {"none", "egg", "bad_egg"}
        ]
        if len(paths) != 493:
            raise ValueError(f"{root} : 493 espèces attendues, {len(paths)} trouvées")
        rows = [_platinum(path) for path in paths]
    elif repo == "pokediamond":
        folder = "personal_pearl" if pearl else "personal"
        source = read_json(root / f"files/poketool/{folder}/personal.json")["baseStats"]
        evolutions = read_json(root / "files/poketool/personal/evo.json")["evos"]
        evos = {r["species"]: r["evos"] for r in evolutions}
        rows = [_diamond(r, evos[r["species"]]) for r in source if r["species"] not in _SPECIAL_DP]
    else:
        raise ValueError(f"Dépôt DS inconnu : {repo}")
    result = {row.identifier: row for row in rows}
    if len(result) != 493 or len(rows) != 493:
        raise ValueError(f"{root} : espèces DS incomplètes ou répétées")
    for row in rows:
        _validate(row)
    return result


def _platinum(path: Path) -> DsSpecies:
    r = read_json(path)
    genders = {
        "MALE_ONLY": 0,
        "FEMALE_12_5": 1,
        "FEMALE_25": 2,
        "FEMALE_50": 4,
        "FEMALE_75": 6,
        "FEMALE_ONLY": 8,
        "NO_GENDER": -1,
    }
    return DsSpecies(
        path.parent.name.replace("_", "-"),
        tuple(r["base_stats"][s] for s in _STATS),
        _constants(r["types"], "TYPE_"),
        _constants(r["abilities"], "ABILITY_", omit_none=True),
        (r["held_items"]["common"], r["held_items"]["rare"]),
        r["catch_rate"],
        genders[r["gender_ratio"].removeprefix("GENDER_RATIO_")],
        r["hatch_cycles"],
        r["exp_rate"].removeprefix("EXP_RATE_"),
        tuple(r["egg_groups"]),
        _platinum_evolutions(r.get("evolutions", []), path),
    )


def _diamond(r: dict, evolutions: list[dict]) -> DsSpecies:
    genders = {0.0: 0, 0.125: 1, 0.25: 2, 0.5: 4, 0.75: 6, 1.0: 8, 2.0: -1}
    return DsSpecies(
        species_identifier(r["species"]),
        tuple(r[s] for s in _DP_STATS),
        _constants(r["types"], "TYPE_"),
        _constants(r["abilities"], "ABILITY_", omit_none=True),
        tuple(r["items"]),
        r["catchRate"],
        genders[r["genderRatio"]],
        r["eggCycles"],
        r["growthRate"],
        tuple(r["eggGroups"]),
        tuple((e["method"], e.get("param", 0), e["target"]) for e in evolutions),
    )


def _platinum_evolutions(rows: list[list], path: Path) -> tuple[tuple[str, int | str, str], ...]:
    if len(rows) > 7 or any(len(e) not in (2, 3) or not e[-1].startswith("SPECIES_") for e in rows):
        raise ValueError(f"{path} : table d'évolution invalide")
    return tuple((e[0], e[1] if len(e) == 3 else 0, e[-1].removeprefix("SPECIES_")) for e in rows)


def _constants(values: list[str], prefix: str, *, omit_none: bool = False) -> tuple[str, ...]:
    if len(values) != 2 or any(not v.startswith(prefix) for v in values):
        raise ValueError(f"Paire de constantes DS invalide : {values}")
    return tuple(
        dict.fromkeys(
            v.removeprefix(prefix).lower().replace("_", "-") for v in values if not omit_none or v != prefix + "NONE"
        )
    )


def _validate(row: DsSpecies) -> None:
    if (
        len(row.stats) != 6
        or any(type(s) is not int or not 1 <= s <= 255 for s in row.stats)
        or not 1 <= row.capture_rate <= 255
        or not 1 <= row.hatch_cycles <= 255
        or not 1 <= len(row.abilities) <= 2
        or not 1 <= len(row.types) <= 2
        or len(row.held_items) != 2
        or len(row.egg_groups) != 2
    ):
        raise ValueError(f"Données personnelles DS invalides : {row.identifier}")
