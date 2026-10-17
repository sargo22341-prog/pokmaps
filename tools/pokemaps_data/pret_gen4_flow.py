"""Flux des scripts DS sous une forme commune aux deux désassemblages : une suite d'étapes reliées.

Platine écrit ses scripts en macros (pret_gen4_scripts) ; Diamant/Perle les a compilés (pret_gen4_script_binary).
Les deux se ramènent aux mêmes commandes du moteur : sauts et appels (conditionnels ou non), retour, fin,
affectations de variables, combats de dresseurs et quelques commandes nommées par les lectures qui en ont
besoin. Les macros composées de Platine (GoToIfEq, CallIfSet, Common_…) sont développées d'après leur définition
dans scrcmd.inc, comme le fait l'assembleur. Toute autre commande garde son nom source et ses arguments.

Un argument vaut un entier quand la source le permet (constante, nombre, #define local), sinon son texte.
Comme ScriptGetVar dans le moteur, un argument de 0x4000 ou plus désigne une variable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_script_binary import ScriptFile
from .pret_gen4_script_commands import ScriptCommand
from .pret_gen4_scripts import FIELD_MACROS, MacroCall, TextScriptFile
from .pret_gen4_source import read_text

VAR_START = 0x4000
# Commandes communes des deux jeux, sous leur nom canonique.
GOTO, GOTO_IF, CALL, CALL_IF, RETURN, END = "goto", "goto_if", "call", "call_if", "return", "end"
SET_VALUE, COPY_VAR = "set_value", "copy_var"
TRAINER_BATTLE, TAG_BATTLE = "trainer_battle", "tag_battle"
# Premier combat de Platine contre le rival (StartFirstBattle, un dresseur) ; celui de Diamant/Perle est un combat
# sauvage (ScrCmd_FirstBattle : espèce et niveau), qui garde son nom source.
FIRST_BATTLE = "first_battle"
COMPARE_VAR, CHECK_FLAG, CHECK_TRAINER, CALL_COMMON = "compare_var", "check_flag", "check_trainer", "call_common"
COMPARE_VALUE = "compare_value"
SET_FLAG, NATIONAL_DEX = "set_flag", "national_dex"
ADD_ITEM, ADD_COINS = "add_item", "add_coins"
RANDOM, PLAYER_STARTER, PLAYER_GENDER = "random", "player_starter", "player_gender"
GAME_VERSION = "game_version"
DATA = "data"
_FLOW = frozenset({GOTO, GOTO_IF, CALL, CALL_IF})
# Commandes qui lisent leurs arguments sans écrire de variable (les sources nomment certains varID).
_READ_ONLY = frozenset(
    {
        COMPARE_VAR,
        COMPARE_VALUE,
        CHECK_FLAG,
        CHECK_TRAINER,
        TRAINER_BATTLE,
        TAG_BATTLE,
        FIRST_BATTLE,
        SET_FLAG,
        CALL_COMMON,
    }
)
_ENDS = frozenset({GOTO, RETURN, END})
# Macros primitives de Platine -> nom canonique.
_PLATINUM = {
    "GoTo": GOTO,
    "GoToIf": GOTO_IF,
    "Call": CALL,
    "CallIf": CALL_IF,
    "Return": RETURN,
    "End": END,
    "SetVarFromValue": SET_VALUE,
    "SetVarFromVar": COPY_VAR,
    "StartTrainerBattle": TRAINER_BATTLE,
    "StartTagBattle": TAG_BATTLE,
    "StartFirstBattle": FIRST_BATTLE,
    "CompareVar": COMPARE_VAR,
    "CompareVarToValue": COMPARE_VALUE,
    "CompareVarToVar": COMPARE_VAR,
    "CheckFlag": CHECK_FLAG,
    "CheckTrainerFlag": CHECK_TRAINER,
    "CallCommonScript": CALL_COMMON,
    "SetFlag": SET_FLAG,
    "GetSetNationalDexEnabled": NATIONAL_DEX,
    "AddItem": ADD_ITEM,
    "AddCoins": ADD_COINS,
    "GetRandom": RANDOM,
    "GetPlayerStarterSpecies": PLAYER_STARTER,
    "GetPlayerGender": PLAYER_GENDER,
    "GetGameVersion": GAME_VERSION,
}
# Opcodes de Diamant/Perle (gScriptCmdTable) -> nom canonique, vérifiés contre le nom de leur fonction.
_DIAMOND_PEARL = {
    0x02: ("ScrCmd_End", END),
    0x11: ("ScrCmd_CompareVarToValue", COMPARE_VALUE),
    0x12: ("ScrCmd_CompareVarToVar", COMPARE_VAR),
    0x14: ("ScrCmd_RunScriptWait", CALL_COMMON),
    0x16: ("ScrCmd_GoTo", GOTO),
    0x1A: ("ScrCmd_Call", CALL),
    0x1B: ("ScrCmd_Return", RETURN),
    0x1C: ("ScrCmd_GoToIf", GOTO_IF),
    0x1D: ("ScrCmd_CallIf", CALL_IF),
    0x1E: ("ScrCmd_SetFlag", SET_FLAG),
    0x20: ("ScrCmd_CheckFlag", CHECK_FLAG),
    0x25: ("ScrCmd_CheckTrainerFlag", CHECK_TRAINER),
    0x28: ("ScrCmd_SetVar", SET_VALUE),
    0x29: ("ScrCmd_CopyVar", COPY_VAR),
    0x79: ("ScrCmd_GiveCoins", ADD_COINS),
    0x7B: ("ScrCmd_GiveItem", ADD_ITEM),
    0xDE: ("ScrCmd_GetStarter", PLAYER_STARTER),
    0x14D: ("ScrCmd_GetPlayerGender", PLAYER_GENDER),
    0x1B7: ("ScrCmd_Random", RANDOM),
    0x246: ("ScrCmd_GetGameVersion", GAME_VERSION),
    0xE5: ("ScrCmd_Unk00E5", TRAINER_BATTLE),
    0x22D: ("ScrCmd_NationalDex", NATIONAL_DEX),
    0x2A0: ("ScrCmd_Unk02A0", TAG_BATTLE),
}
_MAX_EXPANSION_DEPTH = 4
# Paramètres de macro de Platine qui peuvent recevoir une variable écrite par la commande : les sources les nomment
# destVar, result, …Var ; ceux des commandes non documentées (arg0, unk…) sont aussi comptés, par prudence.
_WRITTEN = re.compile(r"dest|result|ret$|out|var$|varid$|^var\d?$|^varid\d?$|^arg\d*$|unk|param", re.IGNORECASE)
_MAX_RANGE = 64

Key = tuple[str, int] | int
Value = int | str


@dataclass(frozen=True)
class Step:
    key: Key
    command: str
    arguments: tuple[Value, ...]
    # Destination d'un saut ou d'un appel ; étape suivante dans le fichier (None après une fin ou un saut).
    target: Key | None
    following: Key | None
    source: str  # macro ou fonction du moteur, pour les messages d'erreur
    # Positions des arguments que la commande peut écrire quand ils désignent une variable.
    writes: frozenset[int] = frozenset()


@dataclass(frozen=True)
class ScriptFlow:
    name: str
    entries: tuple[Key, ...]  # point d'entrée de chaque script, dans l'ordre (numéro de script 1, 2…)
    steps: dict[Key, Step]

    def step(self, key: Key) -> Step:
        found = self.steps[key]
        if found.command == DATA:
            raise ValueError(f"{self.name} : le flux atteint des données ({found.source}, {key})")
        return found


def is_var(value: Value) -> bool:
    return isinstance(value, int) and value >= VAR_START


@dataclass(frozen=True)
class _Template:
    """Corps d'une macro composée de Platine : appels d'autres macros, paramètres « \\nom »."""

    parameters: tuple[tuple[str, str | None, bool], ...]  # nom, valeur par défaut, obligatoire
    body: tuple[tuple[str, tuple[str, ...]], ...]


def read_platinum_macros(root: Path) -> tuple[dict[str, _Template], dict[str, frozenset[int]]]:
    """Macros de scrcmd.inc et movement.inc : modèles des macros faites uniquement d'appels d'autres macros (sans
    directive ni .if), et, pour toutes, les positions des paramètres qui peuvent recevoir une variable écrite."""
    templates = {}
    writes = {}
    text = "\n".join(read_text(root / relative) for relative in FIELD_MACROS)
    for match in re.finditer(r"^\s*\.macro\s+(\w+)([^\n]*)\n(.*?)^\s*\.endm", text, re.MULTILINE | re.DOTALL):
        name, parameters, body = match.groups()
        parsed = _parameters(parameters)
        writes[name] = frozenset(index for index, (parameter, _, _) in enumerate(parsed) if _WRITTEN.search(parameter))
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if not lines or any(line.startswith(".") for line in lines) or name in _PLATINUM:
            continue
        calls = []
        for line in lines:
            macro, _, rest = line.partition(" ")
            calls.append((macro, tuple(part.strip() for part in rest.split(",")) if rest.strip() else ()))
        templates[name] = _Template(parsed, tuple(calls))
    return templates, writes


def _parameters(text: str) -> tuple[tuple[str, str | None, bool], ...]:
    result = []
    for part in (piece for piece in re.split(r"[\s,]+", re.sub(r"\s*=\s*", "=", text.strip())) if piece):
        name, _, default = part.partition("=")
        result.append((name.removesuffix(":req"), default or None, name.endswith(":req")))
    return tuple(result)


@dataclass(frozen=True)
class PlatinumContext:
    """Ce qu'il faut pour lire les macros de Platine : modèles composés, macros de mouvement, constantes."""

    templates: dict[str, _Template]
    writes: dict[str, frozenset[int]]
    movements: frozenset[str]
    constants: dict[str, int]


def platinum_flow(script: TextScriptFile, context: PlatinumContext) -> ScriptFlow:
    rows: list[tuple[str, int, str, tuple[str, ...]]] = []
    starts: dict[str, int] = {}
    for label, calls in script.labels.items():
        starts[label] = len(rows)
        for call in calls:
            rows += [(label, call.line, name, args) for name, args in _expand(call, context, script)]
    keys: list[Key] = [(label, index) for index, (label, *_rest) in enumerate(rows)]
    steps = {}
    for index, (_label, line, name, args) in enumerate(rows):
        following = keys[index + 1] if index + 1 < len(keys) else None
        steps[keys[index]] = _platinum_step(keys[index], name, args, following, starts, keys, script, context, line)
    entries = tuple(_label_key(label, starts, keys, script.name) for label in script.entries)
    return ScriptFlow(script.name, entries, steps)


def _label_key(label: str, starts: dict[str, int], keys: list[Key], where: str) -> Key:
    if label not in starts or starts[label] >= len(keys):
        raise ValueError(f"{where} : label sans instruction : {label}")
    return keys[starts[label]]


def _expand(
    call: MacroCall, context: PlatinumContext, script: TextScriptFile, depth: int = 0
) -> list[tuple[str, tuple[str, ...]]]:
    where = script.name
    if depth > _MAX_EXPANSION_DEPTH:
        raise ValueError(f"{where}:{call.line} : macro {call.name} trop imbriquée")
    name, args = call.name, call.arguments
    if name.startswith(".") or name in context.movements:
        return [(DATA, args)]
    if name == "SetVar":
        value = _value(args[1], script.defines, context.constants)
        return [("SetVarFromVar" if is_var(value) else "SetVarFromValue", args)]
    if name == "GoToIfInRange":
        return _range(call, context, script)
    if name in _PLATINUM or name not in context.templates:
        return [(name, args)]
    template = context.templates[name]
    if len(args) > len(template.parameters):
        raise ValueError(f"{where}:{call.line} : trop d'arguments pour {name}")
    values = {}
    for index, (parameter, default, required) in enumerate(template.parameters):
        given = args[index] if index < len(args) and args[index] else default
        if given is None and required:
            raise ValueError(f"{where}:{call.line} : argument obligatoire absent pour {name} : {parameter}")
        # Comme l'assembleur GNU, un paramètre facultatif omis et sans valeur par défaut est vide.
        values[parameter] = given or ""
    result = []
    for inner, inner_args in template.body:
        substituted = tuple(_substitute(argument, values, where, call.line) for argument in inner_args)
        result += _expand(MacroCall(call.line, inner, substituted), context, script, depth + 1)
    return result


def _substitute(argument: str, values: dict[str, str], where: str, line: int) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1) not in values:
            raise ValueError(f"{where}:{line} : paramètre de macro inconnu : {match.group(1)}")
        return values[match.group(1)]

    return re.sub(r"\\(\w+)", replace, argument)


def _range(call: MacroCall, context: PlatinumContext, script: TextScriptFile) -> list[tuple[str, tuple[str, ...]]]:
    """GoToIfInRange se développe en une comparaison et un saut par valeur, de `lower` à `upper` inclus."""
    var, lower, upper, label = call.arguments
    where = script.name
    low, high = (_value(bound, script.defines, context.constants) for bound in (lower, upper))
    if not isinstance(low, int) or not isinstance(high, int) or not 0 <= high - low < _MAX_RANGE:
        raise ValueError(f"{where}:{call.line} : bornes de GoToIfInRange illisibles : {lower}, {upper}")
    result: list[tuple[str, tuple[str, ...]]] = []
    for value in range(low, high + 1):
        result += [("CompareVar", (var, str(value))), ("GoToIf", ("1", label))]
    return result


def _platinum_step(
    key: Key,
    name: str,
    args: tuple[str, ...],
    following: Key | None,
    starts: dict[str, int],
    keys: list[Key],
    script: TextScriptFile,
    context: PlatinumContext,
    line: int,
) -> Step:
    command = DATA if name == DATA else _PLATINUM.get(name, name)
    source = f"{name} (ligne {line})"
    if command in _FLOW:
        target = _label_key(args[-1], starts, keys, script.name)
        values = tuple(_value(arg, script.defines, context.constants) for arg in args[:-1])
        return Step(key, command, values, target, following, source)
    values = tuple(_value(arg, script.defines, context.constants) for arg in args)
    if name == "CompareVar" and isinstance(values[1], int):
        permanent = range(context.constants.get("VARS_START", VAR_START), context.constants.get("VARS_END", 0x8000) + 1)
        local = range(0x8000, context.constants.get("SCRIPT_LOCAL_VARS_END", 0x800D) + 1)
        if values[1] not in permanent and values[1] not in local:
            command = COMPARE_VALUE
    if command == TRAINER_BATTLE:
        values = (*values, 0) if len(values) == 1 else values
    writes = frozenset() if command in _READ_ONLY else context.writes.get(name, frozenset())
    return Step(key, command, values, None, following, source, frozenset(i for i in writes if i < len(values)))


def _value(text: str, defines: dict[str, str], constants: dict[str, int]) -> Value:
    for _ in range(_MAX_EXPANSION_DEPTH):
        if text not in defines:
            break
        text = defines[text]
    if text in constants:
        return constants[text]
    try:
        return int(text, 0)
    except ValueError:
        return text


def diamond_pearl_flow(name: str, script: ScriptFile, commands: tuple[ScriptCommand, ...]) -> ScriptFlow:
    for opcode, (function, _) in _DIAMOND_PEARL.items():
        if commands[opcode].name != function:
            raise ValueError(f"{name} : commande {opcode:#x} attendue {function}, lue {commands[opcode].name}")
    steps = {}
    for offset, instruction in script.instructions.items():
        source = f"{instruction.name} ({offset:#x})"
        _, command = _DIAMOND_PEARL.get(instruction.opcode, (instruction.name, instruction.name))
        following = offset + instruction.size if offset + instruction.size in script.instructions else None
        arguments: tuple[Value, ...] = instruction.arguments
        target = None
        if command in _FLOW:
            target, arguments = instruction.arguments[-1], instruction.arguments[:-1]
        roles = _roles(commands[instruction.opcode], arguments)
        writes = frozenset() if command in _READ_ONLY else _dp_writes(commands[instruction.opcode], roles, arguments)
        steps[offset] = Step(offset, command, arguments, target, following, source, writes)
    return ScriptFlow(name, script.entries, steps)


def reachable(flow: ScriptFlow, entry: Key) -> set[Key]:
    """Étapes atteintes depuis `entry` en suivant sauts, branches et appels, sans regarder les conditions."""
    seen: set[Key] = set()
    pending = [entry]
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        step = flow.step(key)
        if step.target is not None:
            pending.append(step.target)
        if step.command not in _ENDS and step.following is not None:
            pending.append(step.following)
    return seen


def _roles(command: ScriptCommand, arguments: tuple[Value, ...]) -> list[str]:
    """Rôle de chaque argument, y compris ceux qu'ajoute la valeur du premier (switch du moteur)."""
    roles = [argument.role for argument in command.arguments]
    if command.cases and arguments:
        roles += [argument.role for argument in dict(command.cases).get(int(arguments[0]), ())]
    return roles


def _dp_writes(command: ScriptCommand, roles: list[str], arguments: tuple[Value, ...]) -> frozenset[int]:
    """Arguments qu'une commande de Diamant/Perle peut écrire : ceux lus par ScriptGetVarPointer, et, si elle garde
    un numéro de variable pour l'écrire plus tard (ScrCmd_YesNoMenu), tout argument qui désigne une variable."""
    return frozenset(
        index
        for index, role in enumerate(roles[: len(arguments)])
        if role == "pointer" or (command.stores_var and role in {"value", "var"} and is_var(arguments[index]))
    )
