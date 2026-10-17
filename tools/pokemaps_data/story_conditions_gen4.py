"""Étapes du scénario qu'exigent les chemins des scripts DS, traduites par tools/data/story_events.csv.

Les chemins (pret_gen4_flow_chains) donnent des conditions brutes : drapeau levé ou non, dresseur battu ou non,
comparaison d'une variable ou du résultat d'une commande. Chacune est relue dans pret et décrite dans
story_events.csv pour le dépôt concerné ; une condition absente du fichier arrête la lecture, on ne devine jamais
une étape. Platine nomme ses drapeaux et ses variables (generated/vars_flags.txt) : ses lignes emploient ces noms.
Diamant/Perle ne les nomme pas : ses lignes gardent « flag:N » et « var:N ».

Les choix du joueur ne sont pas des étapes et ne passent pas par le fichier : le Pokémon de départ et le sexe du
joueur sont déjà portés par les variantes des combats (pret_gen4_battles), et la réponse à une question (oui ou
non) ne fait que dérouler la scène.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pret_gen3_conditions import ScriptRequirement
from .pret_gen4_flow import VAR_START
from .pret_gen4_flow_chains import Condition
from .pret_gen4_source import metang_enum
from .story_events import StoryEvents

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

_FILE = "story_events.csv"
_OPERATORS = {"=": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}
_PLAYER_CHOICES = frozenset({"player_starter", "player_gender", "ShowYesNoMenu", "ScrCmd_YesNoMenu"})
_FLAGS = ("flag", "trainer_defeated")


class ScenarioConditions:
    """Traduction des conditions d'un dépôt DS ; les lignes employées sont notées dans `story`."""

    def __init__(self, repo: Gen4PretRepo, story: StoryEvents) -> None:
        self.repo = "pokeplatinum" if repo.platinum else "pokediamond"
        self.story = story
        self.names: dict[int, str] = {}
        if repo.platinum:
            self.names = _flag_and_var_names(metang_enum(repo.root / "generated/vars_flags.txt"))

    def phrases(self, conditions: tuple[Condition, ...], where: str) -> tuple[str, ...]:
        """Étapes du scénario d'un chemin, dans l'ordre des conditions et sans doublon."""
        result: list[str] = []
        for condition in conditions:
            phrase = self._phrase(condition, where)
            if phrase and phrase not in result:
                result.append(phrase)
        return tuple(result)

    def _phrase(self, condition: Condition, where: str) -> str:
        if condition.subject in _PLAYER_CHOICES:
            return ""
        kind, _, number = condition.subject.partition(":")
        if kind in _FLAGS:
            return self._flag(condition, where)
        subject = self._name(condition.subject) if kind == "var" and number.isdigit() else condition.subject
        value = condition.value
        if isinstance(value, str) and value.startswith("var:"):
            value = self._name(value)
        elif not isinstance(value, int):
            raise ValueError(f"{_FILE} : valeur non résolue : {condition} ({self.repo}, {where})")
        key = (self.repo, ScriptRequirement(subject, _OPERATORS[condition.operator], str(value)))
        if key not in self.story.values:
            raise ValueError(f"{_FILE} : comparaison {key[1]} ({self.repo}) à relire dans pret ({where})")
        self.story.used_values.add(key)
        return self.story.values[key].phrase

    def _flag(self, condition: Condition, where: str) -> str:
        if condition.operator != "=" or condition.value not in (0, 1):
            raise ValueError(f"{_FILE} : drapeau non booléen : {condition} ({self.repo}, {where})")
        subject = self._name(condition.subject) if condition.subject.startswith("flag:") else condition.subject
        key = (self.repo, subject)
        if key not in self.story.events:
            state = "levé" if condition.value else "baissé"
            raise ValueError(f"{_FILE} : drapeau {subject} ({self.repo}, {state}) à relire dans pret ({where})")
        self.story.used.add(key)
        event = self.story.events[key]
        return event.when_set if condition.value else event.when_clear

    def _name(self, subject: str) -> str:
        """Nom Platine d'un drapeau ou d'une variable (« flag:N », « var:N ») ; Diamant/Perle garde le numéro."""
        number = int(subject.partition(":")[2])
        if not self.names:
            return subject
        if number not in self.names:
            raise ValueError(f"{self.repo} : drapeau ou variable {number} sans nom unique dans vars_flags.txt")
        return self.names[number]


def _flag_and_var_names(values: dict[str, int]) -> dict[int, str]:
    """Nom de chaque drapeau (FLAG_…, sous 0x4000) et variable (VAR_…) ; les bornes de plages (…_START, …_END) qui
    partagent leur numéro sont écartées, et un numéro porté par deux noms reste sans nom."""
    names: dict[int, str] = {}
    shared: set[int] = set()
    for name, value in values.items():
        prefix = "VAR_" if value >= VAR_START else "FLAG_"
        if not name.startswith(prefix):
            continue
        if value in names:
            shared.add(value)
        names[value] = name
    unique = {value: name for value, name in names.items() if value not in shared}
    # Ces deux alias sont les noms employés dans les scripts, pas des bornes de plage.
    for alias in ("VAR_RESULT", "VAR_LAST_TALKED"):
        if alias in values:
            unique[values[alias]] = alias
    return unique
