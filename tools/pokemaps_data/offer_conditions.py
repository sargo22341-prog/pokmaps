"""Conditions d'une offre de personnage : moments de la journée, jours de la semaine et étapes du scénario.

Une condition est **nécessaire** : l'offre n'est possible que si elle est remplie, sur tous les chemins du script
qui mènent à l'offre. Les scripts sont lus par une analyse de flot « doit être vrai » (`solve`) : à chaque point
du script, l'état réunit ce qui est certain sur tous les chemins qui y arrivent. À une jonction, les moments et les
jours possibles se réunissent, et seules les exigences communes aux deux chemins restent. On ne prétend donc
jamais qu'une offre exige ce qu'un autre chemin du script n'exige pas.

Les exigences restent ici des drapeaux pret (EVENT_…, ENGINE_…, BIT_…BADGE, TOGGLE_…) ; tools/data/story_events.csv
dit lesquels sont des étapes du scénario à afficher (story_events.py).
"""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass, replace

# Moments de la journée (2e génération, shift_const MORN, DAY, NITE de constants/ram_constants.asm).
TIMES_OF_DAY = ("MORN", "DAY", "NITE")
ALL_TIMES = (1 << len(TIMES_OF_DAY)) - 1
# Jours de la semaine, dans l'ordre des constantes pret (SUNDAY vaut 0).
WEEKDAYS = ("SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY")
ALL_WEEKDAYS = (1 << len(WEEKDAYS)) - 1
# Nombre maximal d'états examinés par `solve` pour un script : bien au-delà des plus longs scripts de pret.
_MAX_STEPS = 200_000


@dataclass(frozen=True, order=True)
class Requirement:
    """Drapeau pret dont l'offre exige la valeur `value` (levé ou non)."""

    flag: str
    value: bool


@dataclass(frozen=True)
class Condition:
    """Ce qui est certain à un point d'un script : moments et jours possibles, drapeaux de valeur connue."""

    times: int = ALL_TIMES  # masque des moments possibles (bit i = TIMES_OF_DAY[i])
    weekdays: int = ALL_WEEKDAYS  # masque des jours possibles (bit i = WEEKDAYS[i])
    requirements: frozenset[Requirement] = frozenset()

    def join(self, other: Condition) -> Condition:
        """Ce qui reste certain quand on arrive par l'un ou l'autre chemin."""
        return Condition(
            self.times | other.times, self.weekdays | other.weekdays, self.requirements & other.requirements
        )

    def meet(self, other: Condition) -> Condition:
        """Les deux conditions à la fois (personnage présent seulement la nuit, et offre du lundi)."""
        return Condition(
            self.times & other.times, self.weekdays & other.weekdays, self.requirements | other.requirements
        )

    def with_times(self, mask: int) -> Condition:
        return replace(self, times=self.times & mask)

    def with_weekdays(self, mask: int) -> Condition:
        return replace(self, weekdays=self.weekdays & mask)

    def requiring(self, flag: str, value: bool) -> Condition:
        return replace(self, requirements=self.requirements | {Requirement(flag, value)})

    def without(self, flags: frozenset[str]) -> Condition:
        """Sans les exigences sur `flags` (drapeaux que le script lui-même lève : « déjà donné »)."""
        return replace(self, requirements=frozenset(r for r in self.requirements if r.flag not in flags))

    @property
    def possible(self) -> bool:
        """Faux si aucun moment ou aucun jour ne convient, ou si un drapeau doit être à la fois levé et baissé."""
        flags = [requirement.flag for requirement in self.requirements]
        return bool(self.times and self.weekdays) and len(flags) == len(set(flags))


ALWAYS = Condition()


def time_mask(names: frozenset[str] | set[str]) -> int:
    """Masque des moments nommés (MORN, DAY, NITE) ; un ensemble vide veut dire « toujours »."""
    if not names:
        return ALL_TIMES
    unknown = set(names) - set(TIMES_OF_DAY)
    if unknown:
        raise ValueError(f"Moments de la journée inconnus : {sorted(unknown)}")
    return sum(1 << TIMES_OF_DAY.index(name) for name in names)


def weekday_mask(name: str) -> int:
    if name not in WEEKDAYS:
        raise ValueError(f"Jour de la semaine inconnu : {name}")
    return 1 << WEEKDAYS.index(name)


Transfer = Callable[[Hashable, Condition], list[tuple[Hashable, Condition]]]


def solve(entries: list[tuple[Hashable, Condition]], transfer: Transfer) -> dict[Hashable, Condition]:
    """Condition certaine à chaque point atteignable d'un script.

    `transfer(point, condition)` donne les points suivants avec la condition qui leur arrive. Les conditions se
    réunissent (`Condition.join`) jusqu'à ce qu'aucune ne change : les moments et jours ne font que croître et les
    exigences que décroître, ce qui borne le calcul ; `_MAX_STEPS` l'arrête en erreur s'il dépassait tout script."""
    states: dict[Hashable, Condition] = {}
    pending: list[Hashable] = []
    for point, condition in entries:
        _merge(states, pending, point, condition)
    steps = 0
    while pending:
        steps += 1
        if steps > _MAX_STEPS:
            raise ValueError(f"Analyse des conditions trop longue à partir de {entries[0][0]}")
        point = pending.pop()
        for following, condition in transfer(point, states[point]):
            _merge(states, pending, following, condition)
    return states


def _merge(states: dict[Hashable, Condition], pending: list[Hashable], point: Hashable, condition: Condition) -> None:
    old = states.get(point)
    new = condition if old is None else old.join(condition)
    if new != old:
        states[point] = new
        pending.append(point)
