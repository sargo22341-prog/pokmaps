"""Étapes du scénario qu'exigent les offres : drapeaux pret relus dans tools/data/story_events.csv.

L'analyse des scripts (offer_conditions) dit quels drapeaux une offre exige, levés ou baissés. Le nom d'un drapeau
ne suffit pas à dire ce qu'il signifie : EVENT_MET_BILL est levé au début de Cristal et baissé quand on rencontre
Léo, ENGINE_TIME_CAPSULE est remis à zéro chaque jour. Chaque drapeau rencontré est donc relu dans pret et décrit :

- `when_set` / `when_clear` : ce qu'affiche l'application quand l'offre exige le drapeau levé / baissé
  (« Après la libération de la Tour Radio ») ; vide si ce n'est pas une étape du scénario (état du jour, appel
  d'un dresseur, détail d'une scène) : l'offre n'affiche alors rien pour ce drapeau ;
- `reason` : où pret lève et baisse le drapeau, pour qu'on puisse le vérifier.

Un drapeau absent du fichier arrête la génération : on ne devine jamais une étape.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field

from .offer_conditions import Condition
from .sources import DATA_DIR

_FILE = "story_events.csv"
_COLUMNS = ["repos", "flag", "when_set", "when_clear", "reason"]


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
        return sorted(f"{repo}:{flag}" for repo, flag in set(self.events) - self.used if repo in repos)


def read_story_events() -> StoryEvents:
    """Lit tools/data/story_events.csv ; un doublon ou une ligne incomplète arrête la génération."""
    with (DATA_DIR / _FILE).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != _COLUMNS:
            raise ValueError(f"{_FILE} : colonnes {reader.fieldnames}, attendu {_COLUMNS}")
        rows = list(reader)
    events: dict[tuple[str, str], StoryEvent] = {}
    for row in rows:
        if not row["flag"] or not row["reason"] or not row["repos"]:
            raise ValueError(f"{_FILE} : dépôt, drapeau et raison obligatoires : {row}")
        for phrase in (row["when_set"], row["when_clear"]):
            if phrase and (phrase != phrase.strip() or not phrase[0].isupper() or phrase.endswith(".")):
                raise ValueError(f"{_FILE} : phrase mal formée pour {row['flag']} : {phrase!r}")
        repos = frozenset(row["repos"].split("|"))
        event = StoryEvent(repos, row["flag"], row["when_set"], row["when_clear"])
        for repo in sorted(repos):
            if (repo, row["flag"]) in events:
                raise ValueError(f"{_FILE} : drapeau {row['flag']} décrit deux fois pour {repo}")
            events[(repo, row["flag"])] = event
    return StoryEvents(events)
