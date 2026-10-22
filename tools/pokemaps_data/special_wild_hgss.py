"""Configurations du concours et du Safari HGSS, sans prédiction de tirage."""

import csv
from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path

from .encounters_hgss import Slot
from .pret_gen4_source import c_defines, read_json

SAFARI_SOURCE = "files/arc/safari_enc.json"
CONTEST_SOURCE = "files/data/mushi/mushi_encount.csv"
_TYPES = ("PLAINS", "FOREST", "PEAK", "WATER")
_PERIODS = ("morn", "day", "nite")
_METHODS = ("land", "surf", "oldrod", "goodrod", "superrod")


@dataclass(frozen=True)
class SafariConfiguration:
    """Âge enregistré de l'habitat, distinct de l'âge des objets et du temps réel."""

    days: int = 0
    blocks: tuple[int, int, int, int] = (0, 0, 0, 0)
    decorative: int = 0
    national: bool = False
    objects_unlocked: bool = False

    def __post_init__(self) -> None:
        if type(self.days) is not int or not 0 <= self.days <= 255:
            raise ValueError("Safari : âge d'habitat attendu entre 0 et 255 jours")
        if (
            type(self.blocks) is not tuple
            or len(self.blocks) != 4
            or any(type(n) is not int or not 0 <= n <= 30 for n in self.blocks)
        ):
            raise ValueError("Safari : quatre comptes de blocs attendus entre 0 et 30")
        if type(self.decorative) is not int or not 0 <= self.decorative <= 30:
            raise ValueError("Safari : nombre d'objets décoratifs invalide")
        if sum(self.blocks) + self.decorative > 30:
            raise ValueError("Safari : trente objets maximum par habitat")

        if type(self.national) is not bool or type(self.objects_unlocked) is not bool:
            raise ValueError("Safari : déblocages booléens requis")
        if (self.days or sum(self.blocks) or self.decorative) and not (self.national and self.objects_unlocked):
            raise ValueError("Safari : National et objets débloqués requis")

    @property
    def points(self) -> tuple[int, ...]:
        age = self.days // 10
        return tuple(
            count * (7 if age >= 25 else 1 + sum(age >= limit for limit in (i, i + 4, i + 9, i + 14, i + 19)))
            for i, count in enumerate(self.blocks, 1)
        )


def safari_slots(table: dict, period: str, config: SafariConfiguration, species: dict[str, int]) -> tuple[Slot, ...]:
    if period not in _PERIODS:
        raise ValueError(f"Safari : horaire inconnu : {period}")
    base = table["mons"][period]
    bonuses = table["bonus_mons"]
    if len(base) != 10 or len(bonuses) > 30:
        raise ValueError("Safari : dix emplacements et au plus trente candidats attendus")
    selected = []
    points = dict(zip(_TYPES, config.points, strict=True))
    for bonus in bonuses:
        conditions = bonus["conditions"]
        if not 1 <= len(conditions) <= 2:
            raise ValueError("Safari : une ou deux exigences attendues")
        eligible = True
        for condition in conditions:
            kind = condition["object_type"].removeprefix("SAFARI_ZONE_OBJECT_TYPE_")
            count = condition["count"]
            if kind not in points or type(count) is not int or not 0 <= count <= 255:
                raise ValueError(f"Safari : exigence invalide : {condition}")
            eligible = eligible and points[kind] >= count
        if eligible and len(selected) < 10:
            selected.append(bonus[period])
    mons = selected + base[len(selected) :]
    return tuple(Slot(species[m["species"]], m["level"], m["level"], 10) for m in mons)


def contest_slots(rows: list[dict], weekday: int, national: bool, species: dict[str, int]) -> tuple[Slot, ...]:
    """Jours ISO : lundi = 0 ; le moteur DS utilise dimanche = 0."""
    if type(weekday) is not int or weekday not in (1, 3, 5) or type(national) is not bool:
        raise ValueError("Concours : mardi, jeudi ou samedi et état National booléen requis")
    if len(rows) != 40:
        raise ValueError("Concours : quatre tables de dix Pokémon attendues")
    index = (weekday + 1) // 2 if national else 0
    selected = rows[index * 10 : (index + 1) * 10]
    thresholds = [100] + [int(row["rate"]) for row in selected]
    if thresholds[-1] != 0 or any(a <= b for a, b in pairwise(thresholds)):
        raise ValueError("Concours : seuils cumulés invalides")
    return tuple(
        Slot(species[row["species"]], int(row["lvlmin"]), int(row["lvlmax"]), thresholds[i] - thresholds[i + 1])
        for i, row in enumerate(selected)
    )


def read_special_wild(root: Path) -> dict:
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    with (root / CONTEST_SOURCE).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    safari = read_json(root / SAFARI_SOURCE)["encounters"]
    if len(safari) != 12 or len({area["area"] for area in safari}) != 12:
        raise ValueError("Safari : douze habitats distincts attendus")
    for area in safari:
        for method in _METHODS:
            for period in _PERIODS:
                safari_slots(area[method], period, SafariConfiguration(), species)
                safari_slots(
                    area[method],
                    period,
                    SafariConfiguration(255, (7, 7, 8, 8), national=True, objects_unlocked=True),
                    species,
                )
    return {
        "contest": [
            {
                "weekday": day,
                "national": national,
                "slots": [asdict(s) for s in contest_slots(rows, day, national, species)],
            }
            for national in (False, True)
            for day in (1, 3, 5)
        ],
        "safari": safari,
        "species_ids": species,
        "limits": {"areas": 12, "active_areas": 6, "objects": 30, "days": 255, "slots": 10, "candidates": 30},
        "probability_fr": "Concours : taux conditionnels au jour et au National. Safari : chaque emplacement vaut "
        "10 % après remplacement des dix premiers candidats admissibles dans l’ordre natif. "
        "Sans configuration, aucun taux d’espèce global. Aucun tirage ni résultat de capture prédit.",
        "maturation_fr": "Âge enregistré de l’habitat, plafonné à 255 jours ; multiplicateurs par dizaines de jours. "
        "Les objets décoratifs comptent dans la limite de 30 mais ne donnent aucun point. "
        "Le déblocage des objets et l’âge de l’habitat sont des prérequis déclarés, sans calcul de date réelle.",
    }
