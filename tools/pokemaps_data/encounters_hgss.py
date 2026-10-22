"""Configurations compatibles HGSS et distributions conditionnelles, sans simulation du joueur."""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


class Period(StrEnum):
    MORNING = "morn"
    DAY = "day"
    NIGHT = "nite"


class Radio(StrEnum):
    OFF = "off"
    HOENN = "hoenn"
    SINNOH = "sinnoh"


@dataclass(frozen=True)
class Configuration:
    period: Period = Period.DAY
    radio: Radio = Radio.OFF
    swarm: bool = False
    national: bool = False
    weekday: int = 0  # Lundi = 0.

    def __post_init__(self) -> None:
        if not isinstance(self.swarm, bool) or not isinstance(self.national, bool) or type(self.weekday) is not int:
            raise ValueError("HGSS : conditions booléennes ou jour invalides")
        if not isinstance(self.period, Period) or not isinstance(self.radio, Radio) or not 0 <= self.weekday <= 6:
            raise ValueError("HGSS : horaire, radio ou jour invalide")
        days = {Radio.OFF: self.weekday, Radio.HOENN: 2, Radio.SINNOH: 3}
        if self.radio is not Radio.OFF and (not self.national or self.weekday != days[self.radio]):
            raise ValueError("HGSS : radio régionale incompatible avec le jour ou le Pokédex National")
        if self.swarm and not self.national:
            raise ValueError("HGSS : essaim sans Pokédex National")


@dataclass(frozen=True)
class Slot:
    species: int
    minimum: int
    maximum: int
    chance: int

    def __post_init__(self) -> None:
        if not 1 <= self.species <= 493 or not 1 <= self.minimum <= self.maximum <= 100 or not 0 < self.chance <= 100:
            raise ValueError(f"HGSS : emplacement invalide : {self}")


@dataclass(frozen=True)
class Distribution:
    version: str
    bank: int
    method: str
    configuration: Configuration
    rate: int | None
    slots: tuple[Slot, ...]

    def __post_init__(self) -> None:
        if self.version not in ("heartgold", "soulsilver") or not 0 <= self.bank < 540:
            raise ValueError("HGSS : identité de distribution invalide")
        if self.method not in METHOD_NAMES or self.method.startswith("headbutt-") != (self.rate is None):
            raise ValueError("HGSS : méthode ou taux non applicable invalide")
        if self.rate is not None and not 0 < self.rate <= 100:
            raise ValueError("HGSS : taux de déclenchement invalide")
        if sum(slot.chance for slot in self.slots) != 100:
            raise ValueError(f"HGSS : distribution différente de 100 % : {self.bank}/{self.method}")


def configurations() -> tuple[Configuration, ...]:
    """18 configurations représentatives ; les jours sans effet ne sont pas multipliés."""
    return tuple(
        Configuration(period, radio, swarm, radio is not Radio.OFF or swarm, day)
        for period in Period
        for radio, day in ((Radio.OFF, 0), (Radio.HOENN, 2), (Radio.SINNOH, 3))
        for swarm in (False, True)
    )


def signature(slots: tuple[Slot, ...]) -> tuple[tuple[int, int, int, int], ...]:
    """Garde chaque plage de niveaux : deux distributions de niveaux différentes restent distinctes."""
    totals: dict[tuple[int, int, int], int] = {}
    for slot in slots:
        key = (slot.species, slot.minimum, slot.maximum)
        totals[key] = totals.get(key, 0) + slot.chance
    return tuple((*key, chance) for key, chance in sorted(totals.items()))


def filter_distributions(
    tables: tuple[Distribution, ...], version: str, method: str, configuration: Configuration
) -> tuple[Distribution, ...]:
    if version not in ("heartgold", "soulsilver") or method not in METHOD_NAMES:
        raise ValueError(f"HGSS : filtre inconnu : {version}/{method}")
    return tuple(
        t
        for t in tables
        if t.version == version
        and t.method == method
        and (
            method.startswith("headbutt-")
            or (t.configuration.period, t.configuration.radio, t.configuration.swarm)
            == (configuration.period, configuration.radio, configuration.swarm)
        )
    )


METHOD_NAMES = MappingProxyType(
    {
        "walk": "Marche",
        "surf": "Surf",
        "old-rod": "Canne",
        "good-rod": "Super Canne",
        "super-rod": "Méga Canne",
        "rock-smash": "Éclate-Roc",
        "headbutt-common": "Coup d’Boule — arbre commun",
        "headbutt-rare": "Coup d’Boule — arbre rare",
        "headbutt-secret": "Coup d’Boule — arbre particulier",
    }
)
