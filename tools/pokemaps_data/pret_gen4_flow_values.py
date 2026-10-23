"""Valeurs possibles des variables d'un script DS en un point donné, lues en suivant son flux (pret_gen4_flow).

Le parcours part d'un point d'entrée et suit sauts, branches et appels ; chaque appel est analysé avec l'état
de l'appelant (sans confondre deux appelants), et une boucle est parcourue jusqu'à ce que l'état ne change
plus. L'état est l'ensemble des combinaisons possibles des variables suivies, pour garder leurs liens : l'équipe
du rival choisie selon le Pokémon de départ du joueur reste rattachée à ce Pokémon.

Une variable suivie prend la valeur de chaque affectation (SetVar, CopyVar). Une commande de choix lui donne
chacune de ses valeurs possibles : tirage au hasard borné (GetRandom), Pokémon de départ ou sexe du joueur, version
du jeu (domaines donnés par l'appelant, choix gardé dans STARTER_SLOT, GENDER_SLOT et VERSION_SLOT). Une branche
après une comparaison (CompareVar puis GoToIf ou CallIf) ne garde que les combinaisons qui la prennent, avec la table
des conditions du moteur (sConditionTable). Une variable vaut EXTERNAL à l'entrée (valeur fixée par le moteur ou
par un autre script) et UNKNOWN après une commande qui peut l'écrire autrement (Step.writes). Un script commun
(CallCommonScript, RunScriptWait) rend UNKNOWN les variables qu'il peut écrire ; sans son fichier, toutes les
variables locales 0x8000 à 0x800F. Les offres demandent en plus quelques effets (Effects) : additions exactes et
paiements rattachés à l'offre qui les suit.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import product
from math import prod

from .pret_gen4_flow import (
    CALL,
    CALL_COMMON,
    CALL_IF,
    CHECK_FLAG,
    CHECK_TRAINER,
    COMPARE_VALUE,
    COMPARE_VAR,
    COPY_VAR,
    END,
    GAME_VERSION,
    GOTO,
    GOTO_IF,
    PLAYER_GENDER,
    PLAYER_STARTER,
    RANDOM,
    RETURN,
    SET_VALUE,
    Key,
    ScriptFlow,
    Step,
    Value,
    is_var,
    reachable,
)

EXTERNAL = "externe"
UNKNOWN = "inconnue"
# Mémoire du choix fait au premier appel de chaque commande de choix fixée pour la partie : la variable qui le
# reçoit peut être réutilisée ensuite, le choix reste attaché à la combinaison.
STARTER_SLOT, GENDER_SLOT, VERSION_SLOT = -1, -2, -3
_SLOTS = {PLAYER_STARTER: STARTER_SLOT, PLAYER_GENDER: GENDER_SLOT, GAME_VERSION: VERSION_SLOT}
# Paiements gardés jusqu'à l'étape voulue suivante (Effects.payments) : argent, jetons, Points Combat, objet repris.
MONEY_SLOT, COINS_SLOT, POINTS_SLOT, TAKEN_SLOT = -4, -5, -6, -7
TAKEN_QUANTITY_SLOT = -8
PAYMENT_SLOTS = (MONEY_SLOT, COINS_SLOT, POINTS_SLOT, TAKEN_SLOT, TAKEN_QUANTITY_SLOT)
_ADD_VAR = frozenset({"AddVar", "ScrCmd_AddVar"})
_SUB_VAR = frozenset({"SubVar", "ScrCmd_SubVar"})
_WORD = 0xFFFF
_SCRIPT_LOCALS = frozenset(range(0x8000, 0x8010))
# sConditionTable (scrcmd.c) : pour chaque condition de GoToIf/CallIf, résultats de comparaison qui la valident.
_CONDITIONS = {0: {"<"}, 1: {"="}, 2: {">"}, 3: {"<", "="}, 4: {"=", ">"}, 5: {"<", ">"}}
# Un script tient en quelques milliers d'étapes et ses choix en quelques dizaines de combinaisons.
_MAX_STEPS = 2_000_000
_MAX_DEPTH = 16
_MAX_COMBINATIONS = 1024
_MAX_RANDOM = 64
_COMPARISONS = frozenset({COMPARE_VAR, COMPARE_VALUE, CHECK_FLAG, CHECK_TRAINER})

Valuation = tuple[Value, ...]
State = frozenset[Valuation]


@dataclass(frozen=True)
class CommonScripts:
    """Fichier des scripts communs et numéro du premier (2000 dans les deux jeux)."""

    flow: ScriptFlow
    first: int

    def writes(self, script: Value, depth: int = 0) -> frozenset[int]:
        """Variables que le script commun `script` peut écrire, scripts communs qu'il appelle compris."""
        if not isinstance(script, int) or not 0 <= script - self.first < len(self.flow.entries):
            return _SCRIPT_LOCALS
        if depth > _MAX_DEPTH:
            raise ValueError(f"{self.flow.name} : scripts communs trop imbriqués ({script})")
        written: set[int] = set()
        for key in reachable(self.flow, self.flow.entries[script - self.first]):
            step = self.flow.steps[key]
            if step.command == CALL_COMMON:
                written |= self.writes(step.arguments[0], depth + 1)
            positions = frozenset({0}) if step.command in {SET_VALUE, COPY_VAR} else step.writes
            written |= {int(step.arguments[i]) for i in positions if is_var(step.arguments[i])}
        return frozenset(written)


@dataclass(frozen=True)
class Choices:
    """Domaines des commandes de choix : Pokémon de départ du joueur, sexe du joueur et version du jeu (vide : la
    version n'est pas distinguée, la variable qui la reçoit reste inconnue)."""

    starters: frozenset[int]
    genders: frozenset[int]
    versions: frozenset[int] = frozenset()


@dataclass(frozen=True)
class Effects:
    """Lectures demandées par les offres en plus des affectations : additions et soustractions exactes sur les
    variables `arithmetic` (AddVar, SubVar ; une autre variable reste inconnue après elles, car un compteur de boucle
    non borné ne finirait jamais), et paiements. Une commande de `payments` range le montant (ou l'objet repris) lu à
    la place indiquée dans un des PAYMENT_SLOTS ; chaque étape voulue remet ensuite ces paiements à 0."""

    arithmetic: frozenset[int] = frozenset()
    payments: tuple[tuple[str, int, int], ...] = ()  # commande, place du paiement, position de l'argument
    initial: tuple[tuple[int, tuple[int, ...]], ...] = ()
    outputs: tuple[tuple[Key, tuple[tuple[int, int], ...]], ...] = ()
    extra_payment_slots: tuple[int, ...] = ()


@dataclass
class _Analysis:
    flow: ScriptFlow
    tracked: tuple[int, ...]
    wanted: Callable[[Step], bool]
    common: CommonScripts | None
    choices: Choices | None
    comparisons: dict[Key, Step]
    effects: Effects = Effects()
    found: dict[Key, set[Valuation]] = field(default_factory=dict)
    memo: dict[tuple[Key, State], State | None] = field(default_factory=dict)
    steps: int = 0

    def run(self, entry: Key, state: State, stack: tuple[Key, ...]) -> State | None:
        """État au retour du script commencé en `entry` (None s'il ne revient jamais à l'appelant)."""
        if (entry, state) in self.memo:
            return self.memo[entry, state]
        if entry in stack or len(stack) > _MAX_DEPTH:
            raise ValueError(f"{self.flow.name} : appels récursifs ou trop imbriqués vers {entry}")
        states = {entry: state}
        work = [entry]
        returned: State | None = None
        while work:
            key = work.pop()
            self._spend()
            current, step = states[key], self.flow.step(key)
            if self.wanted(step):
                self.found.setdefault(key, set()).update(current)
            if step.command == RETURN:
                returned = _join(returned, current)
            for successor, following in self._successors(step, current, (*stack, entry)):
                merged = states.get(successor, frozenset()) | following
                if merged != states.get(successor):
                    if len(merged) > _MAX_COMBINATIONS:
                        raise ValueError(f"{self.flow.name} : trop de combinaisons de variables en {successor}")
                    states[successor] = merged
                    work.append(successor)
        self.memo[entry, state] = returned
        return returned

    def _spend(self) -> None:
        self.steps += 1
        if self.steps > _MAX_STEPS:
            raise ValueError(f"{self.flow.name} : parcours du flux trop long")

    def _successors(self, step: Step, state: State, stack: tuple[Key, ...]) -> list[tuple[Key, State]]:
        command = step.command
        if command in {RETURN, END}:
            return []
        if command == GOTO:
            return [(_target(step), state)]
        if step.following is None:
            raise ValueError(f"{self.flow.name} : flux sans suite après {step.source}")
        if command in {GOTO_IF, CALL_IF}:
            taken, skipped = self._branch(step, state)
            if command == GOTO_IF:
                return [(key, part) for key, part in ((_target(step), taken), (step.following, skipped)) if part]
            returned = self.run(_target(step), taken, stack) if taken else None
            after = _join(skipped or None, returned)
            return [] if after is None else [(step.following, after)]
        if command == CALL:
            returned = self.run(_target(step), state, stack)
            return [] if returned is None else [(step.following, returned)]
        return [(step.following, frozenset(new for old in state for new in self._effect(step, old)))]

    def _branch(self, step: Step, state: State) -> tuple[State, State]:
        """Combinaisons qui prennent la branche et celles qui la sautent (toutes deux si la lecture l'ignore)."""
        compare = self.comparisons.get(step.key)
        condition = step.arguments[0]
        if condition not in _CONDITIONS:
            raise ValueError(f"{self.flow.name} : condition de saut inconnue : {step.source}")
        if (
            compare is None
            or compare.command not in {COMPARE_VAR, COMPARE_VALUE}
            or compare.arguments[0] not in self.tracked
        ):
            return state, state
        taken, skipped = set(), set()
        for valuation in state:
            outcome = self._compare(compare, valuation)
            if outcome is None or outcome in _CONDITIONS[int(condition)]:
                taken.add(valuation)
            if outcome is None or outcome not in _CONDITIONS[int(condition)]:
                skipped.add(valuation)
        return frozenset(taken), frozenset(skipped)

    def _compare(self, compare: Step, valuation: Valuation) -> str | None:
        left, right = self._read(compare.arguments[0], valuation), compare.arguments[1]
        right = self._read(right, valuation) if compare.command == COMPARE_VAR and is_var(right) else right
        right = right & _WORD if isinstance(right, int) else right
        if not isinstance(left, int) or not isinstance(right, int):
            return None
        return "<" if left < right else "=" if left == right else ">"

    def _read(self, var: Value, valuation: Valuation) -> Value:
        return valuation[self.tracked.index(int(var))] if isinstance(var, int) and var in self.tracked else UNKNOWN

    def _effect(self, step: Step, valuation: Valuation) -> list[Valuation]:
        if self.effects.payments and self.wanted(step):
            for slot in (*PAYMENT_SLOTS, *self.effects.extra_payment_slots):
                valuation = self._assign(valuation, slot, 0)
        arguments, command = step.arguments, step.command
        outcomes = [assignments for key, assignments in self.effects.outputs if key == step.key]
        if outcomes:
            return [self._assign_many(valuation, assignments) for assignments in outcomes]
        payments = [entry for entry in self.effects.payments if entry[0] == command]
        if payments:
            for _, slot, position in payments:
                amount = arguments[position]
                valuation = self._assign(valuation, slot, self._read(amount, valuation) if is_var(amount) else amount)
            return [valuation]
        if command in _ADD_VAR | _SUB_VAR and arguments[0] in self.effects.arithmetic:
            return [self._assign(valuation, arguments[0], self._arithmetic(step, valuation))]
        if command == SET_VALUE:
            return [self._assign(valuation, arguments[0], arguments[1])]
        if command == COPY_VAR:
            return [self._assign(valuation, arguments[0], self._read(arguments[1], valuation))]
        if command == RANDOM and arguments[0] in self.tracked:
            return [self._assign(valuation, arguments[0], value) for value in self._domain(step, valuation)]
        if command in _SLOTS and _SLOTS[command] in self.tracked:
            slot = _SLOTS[command]
            fixed = self._read(slot, valuation)
            domain = (fixed,) if isinstance(fixed, int) else self._domain(step, valuation)
            return [self._assign(self._assign(valuation, slot, value), arguments[0], value) for value in domain]
        if command == CALL_COMMON:
            written = self.common.writes(arguments[0]) if self.common else _SCRIPT_LOCALS
        else:
            written = {int(arguments[i]) for i in step.writes if is_var(arguments[i])}
        result = valuation
        for var in written:
            result = self._assign(result, var, UNKNOWN)
        return [result]

    def _assign_many(self, valuation: Valuation, assignments: tuple[tuple[int, int], ...]) -> Valuation:
        for var, value in assignments:
            valuation = self._assign(valuation, var, value)
        return valuation

    def _arithmetic(self, step: Step, valuation: Valuation) -> Value:
        left, right = self._read(step.arguments[0], valuation), step.arguments[1]
        right = self._read(right, valuation) if is_var(right) else right
        if not isinstance(left, int) or not isinstance(right, int):
            return UNKNOWN
        return (left + right if step.command in _ADD_VAR else left - right) & _WORD

    def _domain(self, step: Step, valuation: Valuation) -> tuple[Value, ...]:
        if step.command == RANDOM:
            bound = step.arguments[1]
            bound = self._read(bound, valuation) if is_var(bound) else bound
            return tuple(range(bound)) if isinstance(bound, int) and 0 < bound <= _MAX_RANDOM else (UNKNOWN,)
        if self.choices is None:
            return (UNKNOWN,)
        domains = {
            PLAYER_STARTER: self.choices.starters,
            PLAYER_GENDER: self.choices.genders,
            GAME_VERSION: self.choices.versions,
        }
        return tuple(sorted(domains[step.command])) or (UNKNOWN,)

    def _assign(self, valuation: Valuation, var: Value, value: Value) -> Valuation:
        if not isinstance(var, int) or var not in self.tracked:
            return valuation
        index = self.tracked.index(int(var))
        return (*valuation[:index], value, *valuation[index + 1 :])


def _target(step: Step) -> Key:
    if step.target is None:
        raise ValueError(f"saut sans destination : {step.source}")
    return step.target


def _join(first: State | None, second: State | None) -> State | None:
    if first is None or second is None:
        return second if first is None else first
    return first | second


def comparisons(flow: ScriptFlow) -> dict[Key, Step]:
    """Comparaison (CompareVar, CheckFlag, CheckTrainerFlag) qui précède immédiatement chaque saut ou appel
    conditionnel, quand elle est seule à y mener."""
    predecessors: dict[Key, list[Step]] = {}
    for step in flow.steps.values():
        if step.following is not None and step.command not in {GOTO, RETURN, END}:
            predecessors.setdefault(step.following, []).append(step)
        if step.target is not None:
            predecessors.setdefault(step.target, []).append(step)
    return {
        key: found[0]
        for key, found in predecessors.items()
        if len(found) == 1 and found[0].command in _COMPARISONS and flow.steps[key].command in {GOTO_IF, CALL_IF}
    }


def tracked_vars(flow: ScriptFlow, seeds: set[int]) -> tuple[int, ...]:
    """Variables à suivre : celles demandées, les sources des copies qui les alimentent et les variables
    comparées avant une branche."""
    tracked = set(seeds)
    compared = (step for step in comparisons(flow).values() if step.command in {COMPARE_VAR, COMPARE_VALUE})
    tracked |= {int(step.arguments[0]) for step in compared if is_var(step.arguments[0])}
    copies = [step.arguments for step in flow.steps.values() if step.command == COPY_VAR]
    changed = True
    while changed:
        changed = False
        for destination, source in copies:
            if destination in tracked and is_var(source) and source not in tracked:
                tracked.add(int(source))
                changed = True
    return tuple(sorted(tracked))


@dataclass(frozen=True)
class FlowValues:
    tracked: tuple[int, ...]
    found: dict[Key, frozenset[Valuation]]

    def values(self, key: Key, var: int) -> frozenset[Value]:
        """Valeurs possibles de `var` à l'étape `key` (vide si l'étape n'est jamais atteinte ou si `var` n'est pas
        suivie, faute de commande de choix dans le fichier)."""
        if var not in self.tracked:
            return frozenset()
        index = self.tracked.index(var)
        return frozenset(valuation[index] for valuation in self.found.get(key, frozenset()))

    def combos(self, key: Key, items: tuple[Value, ...]) -> frozenset[tuple[Value, ...]]:
        """Combinaisons possibles des `items` à l'étape `key` : une variable suivie (ou l'un des choix *_SLOT)
        prend sa valeur, une variable non suivie vaut EXTERNAL, une constante reste elle-même."""
        positions = [self.tracked.index(item) if item in self.tracked else None for item in items]
        return frozenset(
            tuple(
                valuation[position] if position is not None else EXTERNAL if _is_slot_or_var(item) else item
                for item, position in zip(items, positions, strict=True)
            )
            for valuation in self.found.get(key, frozenset())
        )


def _is_slot_or_var(item: Value) -> bool:
    return item in {STARTER_SLOT, GENDER_SLOT, VERSION_SLOT, *PAYMENT_SLOTS} or is_var(item)


def values_at(
    flow: ScriptFlow,
    wanted: Callable[[Step], bool],
    seeds: set[int],
    entries: tuple[Key, ...] | None = None,
    common: CommonScripts | None = None,
    choices: Choices | None = None,
    effects: Effects | None = None,
) -> FlowValues:
    """Combinaisons possibles des variables suivies à chaque étape voulue, depuis les points d'entrée `entries`."""
    effects = effects or Effects()
    slots = {slot for command, slot in _SLOTS.items() if any(step.command == command for step in flow.steps.values())}
    payments = {slot for _, slot, _ in effects.payments}
    tracked = tuple(sorted({*tracked_vars(flow, seeds), *(slots if choices else ()), *payments}))
    analysis = _Analysis(flow, tracked, wanted, common, choices, comparisons(flow), effects)
    domains = dict(effects.initial)
    options = [domains.get(var, (0 if var in payments else EXTERNAL,)) for var in tracked]
    if prod(map(len, options)) > _MAX_COMBINATIONS:
        raise ValueError(f"{flow.name} : trop de combinaisons initiales")
    initial: State = frozenset(product(*options))
    for entry in flow.entries if entries is None else entries:
        analysis.run(entry, initial, ())
    return FlowValues(tracked, {key: frozenset(found) for key, found in analysis.found.items()})
