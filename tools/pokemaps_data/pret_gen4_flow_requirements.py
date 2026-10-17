"""Conditions nécessaires pour atteindre une étape d'un script DS depuis un point d'entrée donné.

Analyse « doit être vrai » : à chaque étape, l'état réunit les conditions (pret_gen4_flow_chains.Condition) vraies
sur tous les chemins qui y mènent depuis le point d'entrée. Un saut ou un appel conditionnel ajoute la condition de
la branche prise ou évitée (Chains.branch) ; à une jonction, seules les conditions communes restent. Un appel est
analysé avec l'état de l'appelant, et l'étape qui le suit garde les conditions communes à ses retours. Une
condition cesse d'être sûre quand une étape peut récrire ce qu'elle compare : variable écrite (affectation,
commande, script commun) ou drapeau levé ou baissé.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .pret_gen4_flow import (
    CALL,
    CALL_COMMON,
    CALL_IF,
    CHECK_FLAG,
    COMPARE_VALUE,
    COMPARE_VAR,
    COPY_VAR,
    END,
    GOTO,
    GOTO_IF,
    RETURN,
    SET_FLAG,
    SET_VALUE,
    Key,
    ScriptFlow,
    Step,
    is_var,
    reachable,
)
from .pret_gen4_flow_chains import Chains, Condition
from .pret_gen4_flow_values import CommonScripts

_CLEAR_FLAG = frozenset({"ClearFlag", "ScrCmd_ClearFlag"})
_MAX_STEPS = 2_000_000
_MAX_DEPTH = 16

# Ce que compare une condition (« var », numéro) ou (« flag », numéro), pour la retirer quand il change ; None pour
# un dresseur battu, que le script ne change pas.
Dependency = tuple[str, int] | None
Fact = tuple[Dependency, Condition]
Facts = frozenset[Fact]


@dataclass
class _Must:
    flow: ScriptFlow
    chains: Chains
    wanted: Callable[[Step], bool]
    common: CommonScripts | None
    found: dict[Key, Facts] = field(default_factory=dict)
    memo: dict[tuple[Key, Facts], Facts | None] = field(default_factory=dict)
    steps: int = 0

    def run(self, entry: Key, state: Facts, stack: tuple[Key, ...]) -> Facts | None:
        """Conditions sûres au retour du script commencé en `entry` (None s'il ne revient jamais à l'appelant)."""
        if (entry, state) in self.memo:
            return self.memo[entry, state]
        if entry in stack or len(stack) > _MAX_DEPTH:
            raise ValueError(f"{self.flow.name} : appels récursifs ou trop imbriqués vers {entry}")
        states = {entry: state}
        work = [entry]
        returned: Facts | None = None
        while work:
            key = work.pop()
            self.steps += 1
            if self.steps > _MAX_STEPS:
                raise ValueError(f"{self.flow.name} : parcours des conditions trop long")
            current, step = states[key], self.flow.step(key)
            if self.wanted(step):
                self.found[key] = self.found[key] & current if key in self.found else current
            if step.command == RETURN:
                returned = current if returned is None else returned & current
            for successor, following in self._successors(step, current, (*stack, entry)):
                old = states.get(successor)
                new = following if old is None else old & following
                if new != old:
                    states[successor] = new
                    work.append(successor)
        self.memo[entry, state] = returned
        return returned

    def _successors(self, step: Step, state: Facts, stack: tuple[Key, ...]) -> list[tuple[Key, Facts]]:
        command = step.command
        if command in {RETURN, END}:
            return []
        if command == GOTO:
            return [(_target(step), state)]
        if step.following is None:
            raise ValueError(f"{self.flow.name} : flux sans suite après {step.source}")
        if command == GOTO_IF:
            if step.target == step.following:
                return [(step.following, state)]
            return [(_target(step), self._with(step, state, True)), (step.following, self._with(step, state, False))]
        if command == CALL_IF:
            returned = self.run(_target(step), self._with(step, state, True), stack)
            skipped = self._with(step, state, False)
            return [(step.following, skipped if returned is None else skipped & returned)]
        if command == CALL:
            returned = self.run(_target(step), state, stack)
            return [] if returned is None else [(step.following, returned)]
        return [(step.following, self._kill(step, state))]

    def _with(self, step: Step, state: Facts, taken: bool) -> Facts:
        condition = self.chains.branch(step, taken)
        if condition is None:
            return state
        compare = self.chains.comparisons[step.key]
        dependency: Dependency = None
        if compare.command in {COMPARE_VAR, COMPARE_VALUE} and is_var(compare.arguments[0]):
            dependency = ("var", int(compare.arguments[0]))
        elif compare.command == CHECK_FLAG and isinstance(compare.arguments[0], int):
            dependency = ("flag", compare.arguments[0])
        return state | {(dependency, condition)}

    def _kill(self, step: Step, state: Facts) -> Facts:
        """Retire les conditions sur ce que l'étape peut récrire."""
        arguments = step.arguments
        changed: set[tuple[str, int]] = set()
        if step.command in {SET_FLAG, *_CLEAR_FLAG} and isinstance(arguments[0], int):
            changed.add(("flag", arguments[0]))
        elif step.command == CALL_COMMON:
            if self.common is None:
                return frozenset(fact for fact in state if fact[0] is None)
            changed |= {("var", var) for var in self.common.writes(arguments[0])}
            changed |= {("flag", flag) for flag in _common_flags(self.common, arguments[0], 0)}
        else:
            positions = frozenset({0}) if step.command in {SET_VALUE, COPY_VAR} else step.writes
            changed |= {("var", int(arguments[i])) for i in positions if is_var(arguments[i])}
        if not changed:
            return state
        every_flag = ("flag", -1) in changed
        return frozenset(
            fact for fact in state if fact[0] not in changed and not (every_flag and fact[0] and fact[0][0] == "flag")
        )


def _common_flags(common: CommonScripts, script: object, depth: int) -> frozenset[int]:
    """Drapeaux que le script commun `script` peut lever ou baisser, scripts communs qu'il appelle compris ; tous
    (un ensemble qui contient -1) si le numéro ne désigne pas un script du fichier commun."""
    if not isinstance(script, int) or not 0 <= script - common.first < len(common.flow.entries):
        return frozenset({-1})
    if depth > _MAX_DEPTH:
        raise ValueError(f"{common.flow.name} : scripts communs trop imbriqués ({script})")
    flags: set[int] = set()
    for key in reachable(common.flow, common.flow.entries[script - common.first]):
        step = common.flow.steps[key]
        if step.command == CALL_COMMON:
            flags |= _common_flags(common, step.arguments[0], depth + 1)
        elif step.command in {SET_FLAG, *_CLEAR_FLAG}:
            flags.add(int(step.arguments[0]) if isinstance(step.arguments[0], int) else -1)
    return frozenset(flags)


def _target(step: Step) -> Key:
    if step.target is None:
        raise ValueError(f"saut sans destination : {step.source}")
    return step.target


def requirements_at(
    flow: ScriptFlow, entry: Key, wanted: Callable[[Step], bool], common: CommonScripts | None
) -> dict[Key, tuple[Condition, ...]]:
    """Conditions nécessaires à chaque étape voulue atteinte depuis `entry`, triées pour une sortie stable."""
    analysis = _Must(flow, Chains(flow), wanted, common)
    analysis.run(entry, frozenset(), ())
    return {
        key: tuple(sorted({condition for _, condition in facts}, key=lambda c: (c.subject, c.operator, str(c.value))))
        for key, facts in analysis.found.items()
    }
