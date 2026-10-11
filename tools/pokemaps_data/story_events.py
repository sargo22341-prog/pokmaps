"""Étapes du scénario qu'exigent les offres : drapeaux pret relus dans tools/data/story_events.csv.

L'analyse des scripts (offer_conditions) dit quels drapeaux une offre exige, levés ou baissés. Le nom d'un drapeau
ne suffit pas à dire ce qu'il signifie : EVENT_MET_BILL est levé au début de Cristal et baissé quand on rencontre
Léo, ENGINE_TIME_CAPSULE est remis à zéro chaque jour. Chaque drapeau rencontré est donc relu dans pret et décrit :

- `when_set` / `when_clear` : ce qu'affiche l'application quand l'offre exige le drapeau levé / baissé
  (« Après la libération de la Tour Radio ») ; vide si ce n'est pas une étape du scénario (état du jour, appel
  d'un dresseur, détail d'une scène) : l'offre n'affiche alors rien pour ce drapeau ;
- `reason` : où pret lève et baisse le drapeau, pour qu'on puisse le vérifier.
- `operator`, `value`, `phrase` : comparaison numérique d'une `VAR_…` et son texte français ;
  ces lignes laissent `when_set` et `when_clear` vides.

Un drapeau absent du fichier arrête la génération : on ne devine jamais une étape.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field

from .offer_conditions import Condition
from .pret_gen3_conditions import ScriptRequirement
from .sources import DATA_DIR

_FILE = "story_events.csv"
_COLUMNS = ["repos", "flag", "when_set", "when_clear", "reason"]
_VALUE_COLUMNS = ["operator", "value", "phrase"]


@dataclass(frozen=True)
class StoryValue:
    phrase: str
    reason: str


@dataclass(frozen=True)
class StoryEvent:
    """Ce que signifie un drapeau pret, levé ou baissé, pour les dépôts `repos`."""

    repos: frozenset[str]
    flag: str
    when_set: str
    when_clear: str


@dataclass
class StoryEvents:
    """Drapeaux relus ; une ligne qui ne sert à aucune offre des jeux générés arrête la génération (`unused`)."""

    events: dict[tuple[str, str], StoryEvent]  # (dépôt pret, drapeau) -> sens
    used: set[tuple[str, str]] = field(default_factory=set)
    values: dict[tuple[str, ScriptRequirement], StoryValue] = field(default_factory=dict)
    used_values: set[tuple[str, ScriptRequirement]] = field(default_factory=set)

    def script_phrases(self, repo: str, requirements: frozenset[ScriptRequirement], where: str) -> tuple[str, ...]:
        """Traduit un chemin GBA ; chaque comparaison doit être relue séparément."""
        result: list[str] = []
        for requirement in sorted(requirements):
            if requirement.subject.startswith("VAR_"):
                try:
                    requirement = ScriptRequirement(
                        requirement.subject, requirement.operator, str(int(requirement.value, 0))
                    )
                except ValueError as error:
                    raise ValueError(f"{_FILE} : valeur non résolue : {requirement} ({where})") from error
            key = (repo, requirement)
            if key in self.values:
                self.used_values.add(key)
                phrase = self.values[key].phrase
            elif requirement.subject.startswith("FLAG_") and requirement.operator in {"eq", "ne"}:
                if requirement.value not in {"TRUE", "FALSE", "0", "1"}:
                    raise ValueError(f"{_FILE} : drapeau non booléen : {requirement} ({where})")
                value = requirement.value in {"TRUE", "1"}
                if requirement.operator == "ne":
                    value = not value
                condition = Condition().requiring(requirement.subject, value)
                phrases = self.phrases(repo, condition, where)
                phrase = phrases[0] if phrases else ""
            else:
                raise ValueError(f"{_FILE} : comparaison {requirement} ({repo}) à relire dans pret ({where})")
            if phrase and phrase not in result:
                result.append(phrase)
        return tuple(result)

    def phrases(self, repo: str, condition: Condition, where: str) -> tuple[str, ...]:
        """Étapes du scénario qu'exige la condition, dans l'ordre des drapeaux et sans doublon."""
        result: list[str] = []
        for requirement in sorted(condition.requirements):
            key = (repo, requirement.flag)
            if key not in self.events:
                value = "levé" if requirement.value else "baissé"
                raise ValueError(f"{_FILE} : drapeau {requirement.flag} ({repo}, {value}) à relire dans pret ({where})")
            self.used.add(key)
            event = self.events[key]
            phrase = event.when_set if requirement.value else event.when_clear
            if phrase and phrase not in result:
                result.append(phrase)
        return tuple(result)

    def unused(self, repos: set[str]) -> list[str]:
        flags = [f"{repo}:{flag}" for repo, flag in set(self.events) - self.used if repo in repos]
        values = [
            f"{repo}:{req.subject}:{req.operator}:{req.value}"
            for repo, req in set(self.values) - self.used_values
            if repo in repos
        ]
        return sorted(flags + values)


def read_story_events() -> StoryEvents:
    """Lit tools/data/story_events.csv ; un doublon ou une ligne incomplète arrête la génération."""
    with (DATA_DIR / _FILE).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames not in (_COLUMNS, _COLUMNS + _VALUE_COLUMNS):
            raise ValueError(f"{_FILE} : colonnes {reader.fieldnames}, attendu {_COLUMNS}")
        rows = list(reader)
    events: dict[tuple[str, str], StoryEvent] = {}
    values: dict[tuple[str, ScriptRequirement], StoryValue] = {}
    for row in rows:
        if not row["flag"] or not row["reason"] or not row["repos"]:
            raise ValueError(f"{_FILE} : dépôt, drapeau et raison obligatoires : {row}")
        for phrase in (row["when_set"], row["when_clear"], row.get("phrase", "")):
            if phrase and (phrase != phrase.strip() or not phrase[0].isupper() or phrase.endswith(".")):
                raise ValueError(f"{_FILE} : phrase mal formée pour {row['flag']} : {phrase!r}")
        repos = frozenset(row["repos"].split("|"))
        if row["flag"].startswith("VAR_"):
            _read_value(row, repos, values)
            continue
        if any(row.get(column) for column in _VALUE_COLUMNS):
            raise ValueError(f"{_FILE} : comparaison réservée aux variables : {row['flag']}")
        event = StoryEvent(repos, row["flag"], row["when_set"], row["when_clear"])
        for repo in sorted(repos):
            if (repo, row["flag"]) in events:
                raise ValueError(f"{_FILE} : drapeau {row['flag']} décrit deux fois pour {repo}")
            events[(repo, row["flag"])] = event
    return StoryEvents(events, values=values)


def _read_value(
    row: dict[str, str], repos: frozenset[str], values: dict[tuple[str, ScriptRequirement], StoryValue]
) -> None:
    operator, value = row.get("operator", ""), row.get("value", "")
    if operator not in {"eq", "ne", "lt", "le", "gt", "ge"} or not value:
        raise ValueError(f"{_FILE} : comparaison incomplète pour {row['flag']}")
    try:
        number = int(value, 0)
    except ValueError as error:
        raise ValueError(f"{_FILE} : valeur illisible pour {row['flag']} : {value}") from error
    if not 0 <= number <= 65535 or row["when_set"] or row["when_clear"]:
        raise ValueError(f"{_FILE} : variable mal formée : {row['flag']}")
    requirement = ScriptRequirement(row["flag"], operator, str(number))
    for repo in sorted(repos):
        key = (repo, requirement)
        if key in values:
            raise ValueError(f"{_FILE} : comparaison décrite deux fois : {repo}:{requirement}")
        values[key] = StoryValue(row.get("phrase", ""), row["reason"])
