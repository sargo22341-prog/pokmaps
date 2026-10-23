"""Configurations minimales bornées du Safari, chaque choix garde quinze tables complètes."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .builder_wild_gen2 import WildEncounter
from .encounters_hgss import signature
from .placement_hgss import read_placement_json
from .sources import PREVIEW_DIR
from .special_wild_hgss import SafariConfiguration, safari_slots

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

_METHODS = (
    ("land", "walk"),
    ("surf", "surf"),
    ("oldrod", "old-rod"),
    ("goodrod", "good-rod"),
    ("superrod", "super-rod"),
)
_PERIODS = (("morn", "time-morning"), ("day", "time-day"), ("nite", "time-night"))


@dataclass(frozen=True)
class SafariData:
    encounters: tuple[WildEncounter, ...]
    conditions: tuple[dict[str, str], ...]


def configurations(habitat: dict) -> tuple[SafariConfiguration, ...]:
    values = {SafariConfiguration()}
    kinds = ("PLAINS", "FOREST", "PEAK", "WATER")
    for days in range(0, 251, 10):
        factors = SafariConfiguration(days, (1, 1, 1, 1), national=True, objects_unlocked=True).points
        for method, _ in _METHODS:
            for bonus in habitat[method]["bonus_mons"]:
                blocks = [0, 0, 0, 0]
                for condition in bonus["conditions"]:
                    index = kinds.index(condition["object_type"].removeprefix("SAFARI_ZONE_OBJECT_TYPE_"))
                    blocks[index] = max(blocks[index], math.ceil(condition["count"] / factors[index]))
                if sum(blocks) <= 30:
                    values.add(SafariConfiguration(days, tuple(blocks), national=True, objects_unlocked=True))
    if len(values) > 26 * 5 * 30 + 1:
        raise ValueError("HGSS : borne des configurations Safari dépassée")
    return tuple(sorted(values, key=lambda c: (c.days, c.blocks, c.national)))


def safari_data(builder: DatabaseBuilder) -> SafariData:
    data = read_placement_json(PREVIEW_DIR / "hgss-encounters/encounters.json")["special_wild"]
    methods = {r["identifier"]: int(r["id"]) for r in builder.api.table("encounter_methods")}
    times = {r["identifier"]: int(r["id"]) for r in builder.api.table("encounter_condition_values")}
    encounters, conditions = [], []
    for area, habitat in enumerate(data["safari"]):
        seen = set()
        for config in configurations(habitat):
            tables = [
                (method, period, safari_slots(habitat[native], period, config, data["species_ids"]))
                for native, method in _METHODS
                for period, _ in _PERIODS
            ]
            fingerprint = tuple(signature(slots) for _, _, slots in tables)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            index = len(seen) - 1
            if index >= 1000:
                raise ValueError(f"HGSS : plus de mille configurations pour l'habitat {area}")
            value = 4000 + area * 1000 + index
            key = f"hgss-safari-{area}-" + ("base" if index == 0 else str(index))
            conditions.append(dict(id=str(value), identifier=key, name_fr=_label(config)))
            for method, period, slots in tables:
                time = times[dict(_PERIODS)[period]]
                for version in (15, 16):
                    encounters.extend(
                        WildEncounter(
                            version,
                            30_343 + area,
                            s.species,
                            methods[method],
                            tuple(sorted((value, time))),
                            s.minimum,
                            s.maximum,
                            s.chance,
                        )
                        for s in slots
                    )
    return SafariData(tuple(encounters), tuple(conditions))


def _label(config: SafariConfiguration) -> str:
    if not any(config.blocks):
        return "Safari — sans blocs"
    points = ", ".join(
        f"{name} {count}" for name, count in zip(("plaine", "forêt", "pic", "eau"), config.blocks, strict=True) if count
    )
    return f"Safari — {points} ; habitat de {config.days} jours ; National et blocs débloqués"
