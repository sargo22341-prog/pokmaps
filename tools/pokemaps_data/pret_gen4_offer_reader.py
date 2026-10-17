"""Commandes d'offre atteintes depuis un point d'entrée de script DS, avec les valeurs de leurs arguments.

Depuis un point d'entrée, le flux mène à des commandes d'offre (pret_gen4_offer_commands) écrites dans le fichier
ou dans un script commun appelé par numéro (CallCommonScript : CommonScript_AddItemQuantity, qui donne l'objet de
VAR_0x8004 en quantité VAR_0x8005, par exemple). Un script commun est lu une fois, depuis son propre point
d'entrée ; un argument qu'il ne fixe pas (valeur EXTERNAL) prend la valeur qu'a la variable chez l'appelant au
moment de l'appel. Chaque combinaison garde aussi la version du jeu et les paiements faits juste avant l'offre
(argent, jetons, Points Combat, objet repris : pret_gen4_flow_values.Effects).

Un objet ou un Pokémon que donne une commande après l'avoir lu dans une table du moteur (lots du Casino, Points
Combat, fossiles) reste inconnu pour le flux : la commande de table porte l'offre, et le don qui la suit est
marqué comme tel. Toute autre valeur inconnue arrête la lecture.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .pret_gen4_battles import battle_choices
from .pret_gen4_fixed import game_versions
from .pret_gen4_flow import ADD_ITEM, CALL_COMMON, Key, ScriptFlow, Step, Value, is_var, reachable
from .pret_gen4_flow_values import (
    COINS_SLOT,
    EXTERNAL,
    MONEY_SLOT,
    PAYMENT_SLOTS,
    POINTS_SLOT,
    TAKEN_QUANTITY_SLOT,
    TAKEN_SLOT,
    UNKNOWN,
    VERSION_SLOT,
    Choices,
    Effects,
    FlowValues,
    values_at,
)
from .pret_gen4_offer_commands import (
    FOSSIL,
    GIVE_POKEMON,
    PAY_COINS,
    PAY_MONEY,
    PAY_POINTS,
    PAY_SHARDS,
    PAYMENTS,
    TABLE_WRITERS,
    TAKE_ITEM,
    OfferCommand,
    offer_commands,
)
from .pret_gen4_offer_rewards import reward_initial, reward_outputs

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

SLOTS = (VERSION_SLOT, *PAYMENT_SLOTS)
_PAYMENT_SLOT = {PAY_MONEY: MONEY_SLOT, PAY_COINS: COINS_SLOT, PAY_POINTS: POINTS_SLOT, TAKE_ITEM: TAKEN_SLOT}
_MAX_DEPTH = 4
# Sortie des commandes de table : objet ou Pokémon écrit (position de l'argument « output »), puis prix.
_CONSUMERS = frozenset({ADD_ITEM, GIVE_POKEMON})


@dataclass(frozen=True)
class FoundOffer:
    key: Key  # étape du flux de départ : la commande, ou l'appel du script commun qui y mène
    source: str  # commande (et appels) pour les messages et l'aperçu
    command: OfferCommand
    file: int  # fichier de scripts où se trouve la commande
    step: Key  # étape de la commande dans ce fichier
    items: tuple[Value, ...]  # arguments utiles de la commande, tels qu'écrits (constante ou numéro de variable)
    # Valeurs des arguments utiles (OfferCommand.arguments), puis de la version et des paiements (SLOTS).
    combos: frozenset[tuple[Value, ...]]
    consumes_table: bool  # don d'un objet ou d'un Pokémon lu par une commande de table


class OfferReader:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo
        self.commands = offer_commands(repo)
        self.versions = game_versions(repo)
        choices = battle_choices(repo)
        self.choices = Choices(choices.starters, choices.genders, frozenset(self.versions))
        self.effects_payments = tuple(
            (name, _PAYMENT_SLOT[command.kind], command.position("amount" if command.kind != TAKE_ITEM else "item"))
            for name, command in self.commands.items()
            if command.kind in PAYMENTS
        ) + tuple(
            (name, TAKEN_QUANTITY_SLOT, command.position("quantity"))
            for name, command in self.commands.items()
            if command.kind == TAKE_ITEM
        )
        self._cache: dict[tuple[int, int], tuple[FoundOffer, ...]] = {}

    def entry(self, file: int, entry: int, depth: int = 0) -> tuple[FoundOffer, ...]:
        """Offres atteintes depuis le point d'entrée `entry` du fichier `file`."""
        if (file, entry) not in self._cache:
            self._cache[file, entry] = self._read(file, entry, depth)
        return self._cache[file, entry]

    def is_offer(self, step: Step) -> bool:
        command = self.commands.get(step.command)
        return command is not None and command.kind not in PAYMENTS and command.kind != PAY_SHARDS

    def _read(self, file: int, entry: int, depth: int) -> tuple[FoundOffer, ...]:
        if depth > _MAX_DEPTH:
            raise ValueError(f"scripts {file} : appels de scripts communs trop imbriqués")
        flow = self._flow(file)
        start = flow.entries[entry]
        keys = reachable(flow, start)
        direct = [flow.steps[key] for key in sorted(keys, key=str) if self.is_offer(flow.steps[key])]
        calls = {}
        for key in sorted(keys, key=str):
            step = flow.steps[key]
            if step.command == CALL_COMMON and (inner := self._called(step, depth)):
                calls[key] = inner
        if not direct and not calls:
            return ()
        seeds = {int(arg) for step in direct for arg in self._read_items(step) if is_var(arg)}
        needed = {key: _external_vars(inner) for key, inner in calls.items()}
        seeds |= {var for found in needed.values() for var in found}
        # Le musée choisit le fossile dans une table déjà lue : suivre son menu entier
        # multiplierait les combinaisons sans apporter de donnée à l'offre.
        fossils = {name for name, command in self.commands.items() if command.kind == FOSSIL}
        has_fossils = any(flow.steps[key].command in fossils for key in keys)
        seeds |= self._payment_seeds(flow, keys, has_fossils)
        wanted = {step.key for step in direct} | set(calls)
        arguments = {step.key: tuple(arg for arg in self._read_items(step) if is_var(arg)) for step in direct}
        arguments |= needed

        def analyse(arithmetic: frozenset[int]) -> FlowValues:
            effects = Effects(
                arithmetic, self.effects_payments, reward_initial(self.repo, flow), reward_outputs(self.repo, flow)
            )
            return values_at(
                flow, lambda step: step.key in wanted, seeds, (start,), self.repo.common_scripts, self.choices, effects
            )

        values = analyse(frozenset())
        unknown = {
            int(var) for key, found in arguments.items() for var in found if UNKNOWN in values.values(key, int(var))
        }
        if unknown:
            values = analyse(frozenset(unknown))
        return self._found(file, direct, calls, needed, flow, values)

    def _payment_seeds(self, flow: ScriptFlow, keys: frozenset[Key], has_fossils: bool) -> set[int]:
        return {
            int(flow.steps[key].arguments[position])
            for key in keys
            for name, slot, position in self.effects_payments
            if flow.steps[key].command == name
            and is_var(flow.steps[key].arguments[position])
            and not (slot in {TAKEN_SLOT, TAKEN_QUANTITY_SLOT} and has_fossils)
        }

    def _found(
        self,
        file: int,
        direct: list[Step],
        calls: dict[Key, tuple[FoundOffer, ...]],
        needed: dict[Key, tuple[int, ...]],
        flow: ScriptFlow,
        values: FlowValues,
    ) -> tuple[FoundOffer, ...]:
        tables = _table_outputs(flow, self.commands)
        result = []
        for step in direct:
            if step.key not in values.found:
                continue
            command = self.commands[step.command]
            items = self._items(step)
            consumes = command.kind in _CONSUMERS and is_var(items[0]) and int(items[0]) in tables
            combos = values.combos(step.key, (*items, *SLOTS))
            found = FoundOffer(step.key, step.source, command, file, step.key, items, combos, consumes)
            result.append(found)
        for key, inner in calls.items():
            if key not in values.found:
                continue
            outer = values.combos(key, (*needed[key], *SLOTS))
            result += [_through(flow.steps[key], found, needed[key], outer) for found in inner]
        return tuple(result)

    def _flow(self, file: int) -> ScriptFlow:
        flow = self.repo.flows[file]
        # Ces commandes assembleur lisent leurs premiers arguments par valeur, puis seulement
        # leurs sorties par pointeur. stores_var est volontairement prudent dans le lecteur général.
        outputs = {"ScrCmd_Unk029B": frozenset({2, 3}), "ScrCmd_Unk029A": frozenset({1}), "ScrCmd_27C": frozenset()}
        return replace(
            flow,
            steps={
                key: replace(step, writes=outputs[step.command]) if step.command in outputs else step
                for key, step in flow.steps.items()
            },
        )

    def _items(self, step: Step) -> tuple[Value, ...]:
        return tuple(step.arguments[position] for _, position in self.commands[step.command].arguments)

    def _read_items(self, step: Step) -> tuple[Value, ...]:
        """Arguments lus par la commande (sans la variable qu'écrit une commande de table)."""
        command = self.commands[step.command]
        return tuple(step.arguments[position] for name, position in command.arguments if name != "output")

    def _called(self, step: Step, depth: int) -> tuple[FoundOffer, ...]:
        script = step.arguments[0]
        if not isinstance(script, int):
            raise ValueError(f"script commun appelé par une valeur illisible : {step.source}")
        found = self.repo.script_ranges.locate(script)
        if found is None:
            raise ValueError(f"script commun {script} hors des tranches communes : {step.source}")
        return self.entry(*found, depth + 1)


def _external_vars(inner: tuple[FoundOffer, ...]) -> tuple[int, ...]:
    """Variables que les offres d'un script commun lisent chez l'appelant : arguments restés EXTERNAL."""
    found = set()
    for offer in inner:
        for combo in offer.combos:
            found |= {
                int(item) for item, value in zip(offer.items, combo, strict=False) if value == EXTERNAL and is_var(item)
            }
    return tuple(sorted(found))


def _through(call: Step, inner: FoundOffer, needed: tuple[int, ...], outer: frozenset[tuple[Value, ...]]) -> FoundOffer:
    """Offre d'un script commun vue depuis l'appel : arguments externes et choix pris chez l'appelant ; un paiement
    fait dans le script commun l'emporte sur celui de l'appelant."""
    count = len(inner.items)
    combos = set()
    for combo in inner.combos:
        for values in outer:
            arguments = tuple(
                values[needed.index(int(item))] if value == EXTERNAL and is_var(item) else value
                for item, value in zip(inner.items, combo[:count], strict=True)
            )
            slots = tuple(
                own if own not in {EXTERNAL, 0} else caller
                for own, caller in zip(combo[count:], values[len(needed) :], strict=True)
            )
            combos.add((*arguments, *slots))
    source = f"{call.source} → {inner.source}"
    combined = frozenset(combos)
    return FoundOffer(
        call.key, source, inner.command, inner.file, inner.step, inner.items, combined, inner.consumes_table
    )


def _table_outputs(flow: ScriptFlow, commands: dict[str, OfferCommand]) -> frozenset[int]:
    """Variables qu'écrivent les commandes de table du fichier (objet ou Pokémon lu dans le moteur)."""
    result = set()
    for step in flow.steps.values():
        command = commands.get(step.command)
        if command is not None and command.kind in TABLE_WRITERS:
            output = step.arguments[command.position("output")]
            if is_var(output):
                result.add(int(output))
    return frozenset(result)
