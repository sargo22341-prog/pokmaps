"""Adaptateur HGSS vers l'analyse pure des flux DS, sans aiguillage Sinnoh."""

from dataclasses import dataclass

from .pret_gen4_flow import ScriptFlow, Step
from .pret_hgss_flow_context import FlowContext
from .pret_hgss_scripts import Script


@dataclass(frozen=True)
class HgssFlow:
    flow: ScriptFlow
    original: dict[int, int]
    entries: dict[str, int]


def hgss_flow(script: Script, context: FlowContext) -> HgssFlow:
    rows, starts, original = [], {}, {}
    for index, instruction in enumerate(script.steps):
        starts[index] = len(rows)
        expanded = _expand(instruction.command, instruction.arguments, context, 0)
        for command, arguments in expanded:
            original[len(rows)] = index
            rows.append((command, arguments, instruction))
    labels = {label: starts[index] for label, index in script.labels.items() if index in starts}
    steps = {}
    for key, (name, arguments, instruction) in enumerate(rows):
        command, args, writes = _canonical(name, arguments, context)
        target = labels[str(args[-1])] if command in {"goto", "goto_if", "call", "call_if"} else None
        if target is not None:
            args = args[:-1]
        following = key + 1 if key + 1 < len(rows) else None
        steps[key] = Step(key, command, args, target, following, f"{name}:{original[key]}:{instruction.line}", writes)
    entries = {label: labels[label] for label in script.entries}
    return HgssFlow(ScriptFlow(script.source, tuple(entries.values()), steps), original, entries)


def _expand(name: str, args: tuple[str, ...], context: FlowContext, depth: int) -> list[tuple[str, tuple[str, ...]]]:
    if depth > 8:
        raise ValueError(f"HGSS : macro trop imbriquée : {name}")
    if name == "ItemVars":
        return [
            ("CopyVar" if value.startswith("VAR_") else "SetVar", (var, value))
            for var, value in zip(("VAR_SPECIAL_x8004", "VAR_SPECIAL_x8005"), args, strict=True)
        ]
    if name in {"Compare", "SetOrCopyVar"}:
        second_is_var = args[1].startswith("VAR_")
        mapped = (
            ("CompareVarToVar" if second_is_var else "CompareVarToValue")
            if name == "Compare"
            else ("CopyVar" if second_is_var else "SetVar")
        )
        return [(mapped, args)]
    if name not in context.macros:
        return [(name, args)]
    parameters, body = context.macros[name]
    values = {}
    for index, parameter in enumerate(parameters):
        key, _, default = parameter.partition("=")
        values[key] = args[index] if index < len(args) else default
    result = []
    for command, parts in body:
        substituted = tuple(_substitute(part, values) for part in parts if part)
        result.extend(_expand(command, substituted, context, depth + 1))
    return result


def _substitute(text: str, values: dict[str, str]) -> str:
    import re

    return re.sub(r"\\(\w+)", lambda match: values[match[1]], text)


def _canonical(name: str, args: tuple[str, ...], context: FlowContext) -> tuple[str, tuple, frozenset[int]]:
    values = tuple(_value(arg, context) for arg in args)
    canonical = {
        "GoTo": "goto",
        "GoToIf": "goto_if",
        "Call": "call",
        "CallIf": "call_if",
        "Return": "return",
        "End": "end",
        "RestartCurrentScript": "end",
        "SetVar": "set_value",
        "CopyVar": "copy_var",
        "CompareVarToValue": "compare_value",
        "CompareVarToVar": "compare_var",
        "CheckFlag": "check_flag",
        "CheckTrainerFlag": "check_trainer",
        "GetStarterChoice": "player_starter",
        "GetPlayerGender": "player_gender",
        "GetGameVersion": "game_version",
        "SetFlag": "set_flag",
        "Random": "random",
    }
    if name == "CallStd":
        return _standard(args[0], values, context)
    writes = context.writes.get(name, frozenset(range(len(values))))
    if name in {
        "SetFlag",
        "ClearFlag",
        "TrainerBattle",
        "MultiBattle",
        "WildBattle",
        "RocketTrapBattle",
        "CompareVarToValue",
        "CompareVarToVar",
        "CheckFlag",
        "CheckTrainerFlag",
        "GoToIf",
        "CallIf",
    }:
        writes = frozenset()
    return canonical.get(name, name), values, frozenset(i for i in writes if i < len(values))


def _value(text: str, context: FlowContext) -> int | str:
    if text in context.constants:
        return context.constants[text]
    try:
        return int(text, 0)
    except ValueError:
        if text.startswith("VAR_"):
            raise ValueError(f"HGSS : variable inconnue : {text}") from None
        return text


def _standard(name: str, values: tuple, context: FlowContext) -> tuple[str, tuple, frozenset[int]]:
    standard = {
        "std_obtain_item_verbose": ("offer_item", (0x8004, 0x8005)),
        "std_give_item_verbose": ("offer_item", (0x8004, 0x8005)),
        "std_pokemart": ("offer_mart", ()),
        "std_special_mart": ("offer_special_mart", (0x8004,)),
        "std_nurse_joy": ("offer_heal", ()),
        "std_daycare_man": ("offer_daycare_man", ()),
        "std_daycare_lady": ("offer_daycare", ()),
        "std_frontier_move_tutor_1": ("offer_tutor", (0,)),
        "std_frontier_move_tutor_2": ("offer_tutor", (1,)),
        "std_frontier_move_tutor_3": ("offer_tutor", (2,)),
        "std_hidden_item_fanfare": ("noop", ()),
    }
    if name in standard:
        command, arguments = standard[name]
        return command, arguments, frozenset()
    return "call_common", values, frozenset()
