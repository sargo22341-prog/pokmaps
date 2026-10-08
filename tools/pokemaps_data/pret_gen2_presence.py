"""Présence des personnages de la 2e génération : ce qu'exige qu'ils soient sur la carte (offer_conditions).

Un personnage est là selon trois choses lues dans pret :

- les moments de son object_event (MapObject.times) ;
- les rappels de la carte qui le montrent ou le cachent selon le jour, le moment ou le scénario
  (pret_gen2_conditions.object_appearance) ;
- le drapeau qui le cache une fois levé (MapObject.event_flag), quand un autre script que le sien le change :
  un personnage qui disparaît seul, une fois son offre faite, n'exige rien de plus.
"""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from .offer_conditions import ALWAYS, Condition, time_mask
from .pret_gen2_conditions import FLAG_WRITES, SHOWING, Gen2Conditions, Point, object_appearance, object_callbacks
from .pret_models import MapObject, PretMap

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo
    from .pret_gen2_scripts import ScriptFile

# Script commun qui lève les drapeaux du début de la partie (engine/events/std_scripts.asm).
_INITIAL_EVENTS = "InitializeEventsScript"


class Gen2Presence:
    """Lecteur de la présence des personnages d'un dépôt pret de la 2e génération (tables lues une fois)."""

    def __init__(self, repo: Gen2PretRepo, conditions: Gen2Conditions, std_scripts: ScriptFile) -> None:
        self.repo = repo
        self.conditions = conditions
        self.std_scripts = std_scripts
        self._appearances: dict[str, dict[str, Condition]] = {}

    def condition(self, pret_map: PretMap, obj: MapObject, points: frozenset[Point]) -> Condition:
        """Ce qu'exige la présence du personnage `obj`, dont le script exécute les lignes `points` (vide s'il n'en
        a pas). Le drapeau qui le cache ne compte pas quand les rappels de la carte règlent déjà sa présence."""
        appearance = self.appearance(pret_map)
        condition = Condition(times=time_mask(obj.times)).meet(appearance.get(obj.const or "", ALWAYS))
        flag = obj.event_flag
        names = {name for name in (flag, obj.const) if name}
        if flag and obj.const not in appearance and self.written_elsewhere(names, points):
            condition = condition.requiring(flag, False)
        return condition

    @cached_property
    def writes(self) -> dict[str, frozenset[Point]]:
        """Drapeau ou objet (constante de object_const_def) -> lignes de tous les scripts qui le lèvent, le baissent,
        le montrent ou le cachent (scripts communs compris, dont les drapeaux levés au début de la partie)."""
        result: dict[str, set[Point]] = {}
        files = {id(script_file): script_file for script_file in self.repo.script_files.values()}
        for script_file in [*files.values(), self.std_scripts]:
            for name, block in script_file.blocks.items():
                for index, line in enumerate(block.lines):
                    if line.split()[0] in FLAG_WRITES:
                        result.setdefault(line.split()[1], set()).add((script_file, name, index))
        return {flag: frozenset(points) for flag, points in result.items()}

    def written_elsewhere(self, names: set[str], points: frozenset[Point]) -> bool:
        """Vrai si un script autre que celui des lignes `points` lève, baisse, montre ou cache l'un des `names`."""
        return any(self.writes.get(name, frozenset()) - points for name in names)

    def appearance(self, pret_map: PretMap) -> dict[str, Condition]:
        """Ce qu'exige la présence des objets que les rappels de la carte montrent ou cachent (object_appearance)."""
        if pret_map.label not in self._appearances:
            script_file = self.repo.script_files[pret_map.label]
            callbacks = frozenset(
                point
                for label in object_callbacks(script_file)
                for point in self.conditions.script_conditions(script_file, label, None)
            )
            persistent = frozenset(
                obj.const for obj in pret_map.objects if obj.const and self._shown_elsewhere(obj, callbacks)
            )
            self._appearances[pret_map.label] = object_appearance(self.conditions, script_file, persistent)
        return self._appearances[pret_map.label]

    @cached_property
    def initial_flags(self) -> frozenset[str]:
        """Drapeaux levés au début de la partie (InitializeEventsScript) : leurs objets sont cachés au départ."""
        return frozenset(
            line.split()[1]
            for line in self.std_scripts.reachable_lines(_INITIAL_EVENTS, None)
            if line.split()[0] in ("setevent", "setflag")
        )

    def _shown_elsewhere(self, obj: MapObject, callbacks: frozenset[Point]) -> bool:
        """Vrai si l'objet peut être visible sans que les rappels le montrent : drapeau baissé au départ, ou objet
        montré par un autre script que les rappels (lignes `callbacks`)."""
        if obj.event_flag is None or obj.event_flag not in self.initial_flags:
            return True
        points = self.writes.get(obj.event_flag, frozenset()) | self.writes.get(obj.const or "", frozenset())
        return any(_command(point) in SHOWING for point in points - callbacks)


def _command(point: Point) -> str:
    script_file, block, index = point
    return script_file.blocks[block].lines[index].split()[0]
