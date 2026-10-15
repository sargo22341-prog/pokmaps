"""Données de base des espèces dans un jeu, lues dans pret : capture, courbe d'expérience, sexe, œufs.

PokéAPI ne donne que les valeurs actuelles de ces attributs ; certaines ont changé depuis les jeux de la 1re à la
3e génération (taux de capture de Rattatac, de Kyogre ou de Rayquaza, éclosion de Marill, groupes d'œufs de
Tarsal). Le jeu fait foi : builder_pokemon écrit ces valeurs par groupe de versions.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

from .games import Game, PretFormat
from .pret_gen3_source import MAX_SOURCE_BYTES, balanced_bodies
from .pret_identifiers import species_identifier
from .pret_source import annotated_lines, macro_args, parse_int
from .pret_species_gen4 import DsSpecies, read_ds_species

# Fichier des données de base des espèces dans chaque dépôt GBA.
GEN3_SOURCES = {
    "pokeruby": "src/data/pokemon/base_stats.h",
    "pokeemerald": "src/data/pokemon/species_info.h",
    "pokefirered": "src/data/pokemon/species_info.h",
}
_MAX_SPECIES = 512
_GROWTH_RATES = {
    "GROWTH_MEDIUM_FAST": "medium",
    "GROWTH_ERRATIC": "slow-then-very-fast",
    "GROWTH_FLUCTUATING": "fast-then-very-slow",
    "GROWTH_MEDIUM_SLOW": "medium-slow",
    "GROWTH_FAST": "fast",
    "GROWTH_SLOW": "slow",
}
# Huitièmes de femelles, -1 pour un Pokémon asexué (comme gender_rate dans PokéAPI).
_GEN2_GENDERS = {
    "GENDER_F0": 0,
    "GENDER_F12_5": 1,
    "GENDER_F25": 2,
    "GENDER_F50": 4,
    "GENDER_F75": 6,
    "GENDER_F100": 8,
    "GENDER_UNKNOWN": -1,
}
_GEN3_GENDERS = {
    "MON_MALE": 0,
    "PERCENT_FEMALE(12.5)": 1,
    "PERCENT_FEMALE(25)": 2,
    "PERCENT_FEMALE(50)": 4,
    "PERCENT_FEMALE(75)": 6,
    "MON_FEMALE": 8,
    "MON_GENDERLESS": -1,
}
# Groupes d'œufs : nom pret de la 2e génération (EGG_…) ou de la 3e (EGG_GROUP_…) -> identifiant PokéAPI.
_EGG_GROUPS = {
    "MONSTER": "monster",
    "WATER_1": "water1",
    "BUG": "bug",
    "FLYING": "flying",
    "GROUND": "ground",
    "FIELD": "ground",
    "FAIRY": "fairy",
    "PLANT": "plant",
    "GRASS": "plant",
    "HUMANSHAPE": "humanshape",
    "HUMAN_LIKE": "humanshape",
    "WATER_3": "water3",
    "MINERAL": "mineral",
    "INDETERMINATE": "indeterminate",
    "AMORPHOUS": "indeterminate",
    "WATER_2": "water2",
    "DITTO": "ditto",
    "DRAGON": "dragon",
    "NONE": "no-eggs",
    "UNDISCOVERED": "no-eggs",
    "NO_EGGS_DISCOVERED": "no-eggs",
}
_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
_T = TypeVar("_T")


@dataclass(frozen=True)
class Breeding:
    """Sexe et œufs d'une espèce, à partir de la 2e génération."""

    gender_rate: int
    hatch_counter: int
    # Identifiants PokéAPI, sans doublon (pret répète le groupe unique d'une espèce).
    egg_groups: tuple[str, ...]


@dataclass(frozen=True)
class SpeciesProfile:
    capture_rate: int
    # Identifiant PokéAPI de la courbe d'expérience.
    growth_rate: str
    # None en 1re génération, qui ne connaît ni sexe ni œufs.
    breeding: Breeding | None


def read_species_profiles(root: Path, game: Game) -> dict[str, SpeciesProfile]:
    """Identifiant PokéAPI de l'espèce -> ses données de base dans le désassemblage de `game` extrait dans `root`."""
    match game.pret_format:
        case PretFormat.GEN1:
            return _read_asm(root, _gen1_profile)
        case PretFormat.GEN2:
            return _read_asm(root, _gen2_profile)
        case PretFormat.GEN3:
            return _read_gen3(root, game.pret_repo)
        case PretFormat.GEN4:
            return ds_profiles(read_ds_species(root, game.pret_repo))


def ds_profiles(rows: dict[str, DsSpecies]) -> dict[str, SpeciesProfile]:
    growth = {key.removeprefix("GROWTH_"): value for key, value in _GROWTH_RATES.items()}
    return {
        name: SpeciesProfile(
            row.capture_rate,
            _known(growth, row.growth, name),
            Breeding(
                row.gender_rate,
                row.hatch_cycles,
                _egg_groups([g.removeprefix("EGG_GROUP_") for g in row.egg_groups], name),
            ),
        )
        for name, row in rows.items()
    }


def _read_asm(root: Path, profile: Callable[[_AsmFields], SpeciesProfile]) -> dict[str, SpeciesProfile]:
    """Un fichier par espèce dans data/pokemon/base_stats ; chaque champ lu doit y figurer une seule fois."""
    paths = sorted((root / "data/pokemon/base_stats").glob("*.asm"))
    if not paths or len(paths) > _MAX_SPECIES:
        raise ValueError(f"{root.name} : {len(paths)} fichiers de données de base")
    result: dict[str, SpeciesProfile] = {}
    for path in paths:
        lines = annotated_lines(path)
        if not lines or not lines[0][0].startswith("db "):
            raise ValueError(f"{path} : espèce introuvable en première ligne")
        species = species_identifier(macro_args(lines[0][0], "db")[0].removeprefix("DEX_"))
        if species in result:
            raise ValueError(f"{path} : espèce répétée {species}")
        result[species] = profile(_AsmFields(path, lines))
    return result


class _AsmFields:
    """Champs d'un fichier de données de base, repérés par leur commentaire de fin de ligne (« ; catch rate »)."""

    def __init__(self, path: Path, lines: list[tuple[str, str]]) -> None:
        self.path = path
        self.lines = lines

    def args(self, comment: str) -> list[str]:
        found = [code for code, note in self.lines if note == comment]
        if len(found) != 1:
            raise ValueError(f"{self.path} : {len(found)} lignes « {comment} »")
        return macro_args(found[0], found[0].split()[0])

    def value(self, comment: str) -> str:
        args = self.args(comment)
        if len(args) != 1:
            raise ValueError(f"{self.path} : valeur « {comment} » invalide : {args}")
        return args[0]


def _gen1_profile(fields: _AsmFields) -> SpeciesProfile:
    return SpeciesProfile(
        parse_int(fields.value("catch rate")), _known(_GROWTH_RATES, fields.value("growth rate"), fields.path), None
    )


def _gen2_profile(fields: _AsmFields) -> SpeciesProfile:
    eggs = fields.args("egg groups")
    if len(eggs) != 2 or not all(egg.startswith("EGG_") for egg in eggs):
        raise ValueError(f"{fields.path} : groupes d'œufs invalides : {eggs}")
    breeding = Breeding(
        _known(_GEN2_GENDERS, fields.value("gender ratio"), fields.path),
        parse_int(fields.value("step cycles to hatch")),
        _egg_groups([egg.removeprefix("EGG_") for egg in eggs], fields.path),
    )
    return SpeciesProfile(
        parse_int(fields.value("catch rate")),
        _known(_GROWTH_RATES, fields.value("growth rate"), fields.path),
        breeding,
    )


def _read_gen3(root: Path, pret_repo: str) -> dict[str, SpeciesProfile]:
    if pret_repo not in GEN3_SOURCES:
        raise ValueError(f"Dépôt GBA sans données de base connues : {pret_repo}")
    path = root / GEN3_SOURCES[pret_repo]
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError(f"{path} : source trop volumineuse")
    # pokeruby écrit « Pokémon » en Latin-1 dans ses commentaires ; le code lu ici est en ASCII.
    text = _COMMENTS.sub("", path.read_bytes().decode("latin-1"))
    result: dict[str, SpeciesProfile] = {}
    for name, body in balanced_bodies(text, r"\[SPECIES_(\w+)\]\s*=\s*\{", _MAX_SPECIES):
        if name == "NONE":
            continue
        species = species_identifier(name)
        if species in result or "#" in body:
            raise ValueError(f"{path} : espèce répétée ou conditionnelle : {name}")
        result[species] = _gen3_profile(body, f"{path} ({name})")
    return result


def _gen3_profile(body: str, where: str) -> SpeciesProfile:
    def field(name: str, pattern: str) -> str:
        found = re.findall(rf"\.{name}\s*=\s*({pattern})\s*,", body)
        if len(found) != 1:
            raise ValueError(f"{where} : {len(found)} champs {name}")
        return found[0]

    eggs = re.findall(r"EGG_GROUP_(\w+)", body)
    if len(eggs) != 2:
        raise ValueError(f"{where} : groupes d'œufs invalides : {eggs}")
    breeding = Breeding(
        _known(_GEN3_GENDERS, re.sub(r"\s", "", field("genderRatio", r"\w+(?:\([\d.\s]+\))?")), where),
        int(field("eggCycles", r"\d+")),
        _egg_groups(eggs, where),
    )
    growth = _known(_GROWTH_RATES, field("growthRate", r"\w+"), where)
    return SpeciesProfile(int(field("catchRate", r"\d+")), growth, breeding)


def _egg_groups(names: list[str], where: object) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_known(_EGG_GROUPS, name, where) for name in names))


def _known(values: dict[str, _T], key: str, where: object) -> _T:
    if key not in values:
        raise ValueError(f"{where} : valeur pret inconnue : {key}")
    return values[key]
