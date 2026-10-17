"""Conditions qui mènent à une étape d'un script DS, lues sur la chaîne d'étapes sans embranchement qui la précède.

En remontant le flux depuis l'étape, tant qu'une seule étape y mène, chaque saut ou appel conditionnel pris (ou
évité) après une comparaison donne une condition : variable comparée et valeur (CompareVar), drapeau défini ou
non (CheckFlag), dresseur battu ou non (CheckTrainerFlag). La variable comparée est nommée par la commande qui l'a
écrite plus haut sur la même chaîne (GetLeagueVictories, player_starter…), sinon par son numéro. La lecture
s'arrête au premier point où plusieurs chemins se rejoignent : elle ne prétend pas décrire tout le scénario.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pret_gen4_flow import (
    CALL_IF,
    CHECK_FLAG,
    CHECK_TRAINER,
    COPY_VAR,
    END,
    GOTO,
    GOTO_IF,
    RETURN,
    SET_VALUE,
    Key,
    ScriptFlow,
    Step,
    is_var,
)
from .pret_gen4_flow_values import comparisons

# sConditionTable (scrcmd.c) : résultats de comparaison (0 inférieur, 1 égal, 2 supérieur) qui valident chaque
# condition de GoToIf/CallIf, et son écriture.
_RESULTS = {0: {0}, 1: {1}, 2: {2}, 3: {0, 1}, 4: {1, 2}, 5: {0, 2}}
_OPERATORS = {0: "<", 1: "=", 2: ">", 3: "<=", 4: ">=", 5: "!="}
_NEGATION = {"=": "!=", "!=": "=", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}
_MAX_CHAIN = 256
_MAX_PATHS = 64
_MAX_PATH_STEPS = 200_000


@dataclass(frozen=True)
class Condition:
    subject: str  # commande qui fixe la valeur comparée, « flag:N », « trainer_defeated:N » ou « var:N »
    operator: str
    value: int | str  # entier, « var:N » pour une autre variable, ou constante restée sans valeur


class Chains:
    def __init__(self, flow: ScriptFlow) -> None:
        self.flow = flow
        self.comparisons = comparisons(flow)
        self.predecessors: dict[Key, list[Step]] = {}
        for step in flow.steps.values():
            if step.following is not None and step.command not in {GOTO, RETURN, END}:
                self.predecessors.setdefault(step.following, []).append(step)
            if step.target is not None:
                self.predecessors.setdefault(step.target, []).append(step)

    def conditions(self, key: Key) -> tuple[Condition, ...]:
        """Conditions de la chaîne sans embranchement qui précède `key`, dans l'ordre du script."""
        conditions: tuple[Condition, ...] = ()
        current, seen = key, frozenset({key})
        for _ in range(_MAX_CHAIN):
            before = self.predecessors.get(current, [])
            if len(before) != 1 or before[0].key in seen:
                break
            current, seen, conditions = self._back(before[0], current, seen, conditions)
        return tuple(dict.fromkeys(reversed(conditions)))

    def _condition(self, compare: Step, code: int, taken: bool) -> Condition | None:
        results = _RESULTS[code] if taken else {0, 1, 2} - _RESULTS[code]
        if compare.command in {CHECK_FLAG, CHECK_TRAINER}:
            # CheckFlag et CheckTrainerFlag rangent 0 (non) ou 1 (oui) comme résultat de comparaison.
            kept = results & {0, 1}
            if len(kept) != 1:
                return None
            subject = "flag" if compare.command == CHECK_FLAG else "trainer_defeated"
            return Condition(f"{subject}:{compare.arguments[0]}", "=", int(1 in kept))
        operator = _OPERATORS[code] if taken else _NEGATION[_OPERATORS[code]]
        value = compare.arguments[1]
        # CompareVar compare aussi deux variables (CompareVarToVar de Diamant/Perle) : la valeur nomme alors la seconde.
        return Condition(self._subject(compare), operator, f"var:{value}" if is_var(value) else value)

    def _subject(self, compare: Step) -> str:
        var = compare.arguments[0]
        current = compare.key
        for _ in range(_MAX_CHAIN):
            before = self.predecessors.get(current, [])
            if len(before) != 1:
                break
            step = before[0]
            written = {0} if step.command in {SET_VALUE, COPY_VAR} else step.writes
            if any(step.arguments[i] == var for i in written):
                return step.command.split(" ")[0]
            current = step.key
        return f"var:{var}"

    def paths(self, key: Key) -> tuple[tuple[Condition, ...], ...]:
        """Conditions de chaque chemin qui mène d'un point d'entrée à `key`, dans l'ordre du script ; un chemin ne
        repasse jamais par la même étape. La recherche est bornée : au-delà, la lecture s'arrête."""
        found: set[tuple[Condition, ...]] = set()
        pending: list[tuple[Key, frozenset[Key], tuple[Condition, ...]]] = [(key, frozenset({key}), ())]
        explored = 0
        while pending:
            explored += 1
            if explored > _MAX_PATH_STEPS or len(found) > _MAX_PATHS:
                raise ValueError(f"{self.flow.name} : trop de chemins vers {key}")
            current, seen, conditions = pending.pop()
            if current in self.flow.entries:
                found.add(tuple(reversed(conditions)))
            for step in self.predecessors.get(current, []):
                if step.key not in seen:
                    pending.append(self._back(step, current, seen, conditions))
        return tuple(sorted(found, key=lambda path: (len(path), repr(path))))

    def _back(
        self, step: Step, current: Key, seen: frozenset[Key], conditions: tuple[Condition, ...]
    ) -> tuple[Key, frozenset[Key], tuple[Condition, ...]]:
        compare = self.comparisons.get(step.key)
        decided = step.command == GOTO_IF or (step.command == CALL_IF and step.target == current)
        if not decided or compare is None or step.target == step.following:
            return step.key, seen | {step.key}, conditions
        condition = self._condition(compare, int(step.arguments[0]), step.target == current)
        added = conditions if condition is None else (*conditions, condition)
        return compare.key, seen | {step.key, compare.key}, added
