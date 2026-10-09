"""Analyse des chemins GBA : appels, drapeaux, variables et comparaisons de scénario."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .pret_gen3_script_values import number_value, range_values, shifted_value
from .pret_gen3_scripts import Gen3Scripts, Instruction

_MAX_STEPS = 100_000
_MAX_CALL_DEPTH = 24
_TEMPORARY = frozenset({"VAR_RESULT", "VAR_FACING", "VAR_LAST_TALKED", "VAR_TEMP_0"})
_INVERSE = {"eq": "ne", "ne": "eq", "lt": "ge", "ge": "lt", "le": "gt", "gt": "le"}
_COMPARISONS = frozenset(_INVERSE)


@dataclass(frozen=True, order=True)
class ScriptRequirement:
    subject: str
    operator: str
    value: str


@dataclass(frozen=True)
class ScriptState:
    point: tuple[str, int]
    stack: tuple[tuple[str, int], ...] = ()
    values: tuple[tuple[str, str], ...] = ()
    requirements: frozenset[ScriptRequirement] = frozenset()
    comparison: tuple[str, str] | None = None

    def value(self, name: str) -> str:
        return dict(self.values).get(name, name)

    def assigning(self, name: str, value: str) -> ScriptState:
        values = dict(self.values)
        values[name] = self.value(value)
        return replace(self, values=tuple(sorted(values.items())))


def _temporary(name: str) -> bool:
    return name in _TEMPORARY or name.startswith(("VAR_0x800", "VAR_TEMP_"))


def _number(value: str) -> int | None:
    if value in {"TRUE", "FALSE", "YES", "NO"}:
        return int(value in {"TRUE", "YES"})
    try:
        return int(value, 0)
    except ValueError:
        return None


def _compare(left: str, operator: str, right: str) -> bool | None:
    a, b = _number(left), _number(right)
    if a is not None and b is not None:
        return {"eq": a == b, "ne": a != b, "lt": a < b, "gt": a > b, "le": a <= b, "ge": a >= b}[operator]
    if left == right:
        return operator in {"eq", "le", "ge"}
    values = range_values(left)
    if values is not None and b is not None:
        outcomes = {_compare(str(number), operator, right) for number in (values.start, values.stop - 1)}
        if operator in {"eq", "ne"} and b in values:
            return None if len(values) > 1 else operator == "eq"
        return outcomes.pop() if len(outcomes) == 1 else None
    return None


def _refine(
    state: ScriptState, subject: str, operator: str, value: str, constants: dict[str, int]
) -> ScriptState | None:
    left, right = state.value(subject), state.value(value)
    # Une VAR non affectée désigne une valeur inconnue, jamais son adresse numérique.
    left_number = None if left.startswith(("VAR_", "FLAG_")) else number_value(left, constants)
    right_number = None if right.startswith(("VAR_", "FLAG_")) else number_value(right, constants)
    result = _compare(
        str(left_number) if left_number is not None else left,
        operator,
        str(right_number) if right_number is not None else right,
    )
    if result is False:
        return None
    if result is True:
        return state
    requirement = ScriptRequirement(subject, operator, value)
    opposite = ScriptRequirement(subject, _INVERSE[operator], value)
    if opposite in state.requirements:
        return None
    if operator == "eq" and any(
        prior.subject == subject and prior.operator == "eq" and prior.value != value for prior in state.requirements
    ):
        return None
    requirements = state.requirements if _temporary(subject) else state.requirements | {requirement}
    if not _possible(requirements):
        return None
    refined = replace(state, requirements=requirements)
    return refined.assigning(subject, value) if operator == "eq" else refined


def _possible(requirements: frozenset[ScriptRequirement]) -> bool:
    for subject in {requirement.subject for requirement in requirements}:
        minimum, maximum = 0, 65535
        excluded = set()
        for requirement in requirements:
            number = _number(requirement.value)
            if requirement.subject != subject or number is None:
                continue
            match requirement.operator:
                case "eq":
                    minimum, maximum = max(minimum, number), min(maximum, number)
                case "ne":
                    excluded.add(number)
                case "gt" | "ge":
                    minimum = max(minimum, number + (requirement.operator == "gt"))
                case "lt" | "le":
                    maximum = min(maximum, number - (requirement.operator == "lt"))
                case _:
                    raise ValueError(f"Comparaison inconnue : {requirement.operator}")
        if maximum < minimum or maximum - minimum + 1 <= sum(minimum <= value <= maximum for value in excluded):
            return False
    return True


def _branch(state: ScriptState, instruction: Instruction, scripts: Gen3Scripts) -> list[ScriptState]:
    command, args = instruction.command, instruction.args
    suffix = command.split("_if_", 1)[1]
    if suffix in {"set", "unset"}:
        subject, value = args[0], "TRUE" if suffix == "set" else "FALSE"
        operator = "eq"
    elif suffix in _COMPARISONS:
        if len(args) == 3:
            subject, value = args[:2]
        elif len(args) == 1 and state.comparison:
            subject, value = state.comparison
        else:
            raise ValueError(f"{instruction.source} : comparaison sans sujet : {instruction}")
        operator = suffix
    else:
        # Tests de combat et mode Memorydex : aucune étape de scénario déductible.
        return _two_edges(state, scripts.target(args[-1]), command.startswith("call"))
    taken = _refine(state, subject, operator, value, scripts.constants)
    skipped = _refine(state, subject, _INVERSE[operator], value, scripts.constants)
    edges = [skipped] if skipped else []
    if taken:
        edges.append(_jump(taken, scripts.target(args[-1]), command.startswith("call")))
    return edges


def _jump(state: ScriptState, target: tuple[str, int], call: bool) -> ScriptState:
    stack = (*state.stack, state.point) if call else state.stack
    if len(stack) > _MAX_CALL_DEPTH:
        raise ValueError(f"{target[0]} : appels de scripts trop profonds")
    return replace(state, point=target, stack=stack)


def _two_edges(state: ScriptState, target: tuple[str, int], call: bool) -> list[ScriptState]:
    return [state, _jump(state, target, call)]


def _battle_edges(state: ScriptState, instruction: Instruction, scripts: Gen3Scripts) -> list[ScriptState]:
    command, args = instruction.command, instruction.args
    target_index = None
    if command == "trainerbattle_single" and len(args) > 3:
        target_index = 3
    elif command == "trainerbattle_double" and len(args) > 4:
        target_index = 4
    elif command == "trainerbattle":
        battle_type = number_value(args[0], scripts.constants)
        if args[0] in {"TRAINER_BATTLE_CONTINUE_SCRIPT", "TRAINER_BATTLE_CONTINUE_SCRIPT_NO_MUSIC"}:
            target_index = 5
        elif args[0] in {"TRAINER_BATTLE_CONTINUE_SCRIPT_DOUBLE", "TRAINER_BATTLE_CONTINUE_SCRIPT_DOUBLE_NO_MUSIC"}:
            target_index = 6
        elif battle_type in {1, 2, 6, 8}:
            target_index = 6 if battle_type in {6, 8} else 5
    if target_index is None:
        return [state]
    if target_index >= len(args):
        raise ValueError(f"{instruction.source} : script après combat absent")
    target = state.value(args[target_index])
    if target in {"FALSE", "0"}:
        return [state]
    # Le moteur peut reprendre le dialogue habituel ou exécuter la scène de victoire.
    return _two_edges(state, scripts.target(target), True)


def _next(state: ScriptState, instruction: Instruction, scripts: Gen3Scripts) -> list[ScriptState]:
    command, args = instruction.command, instruction.args
    after = replace(state, point=(state.point[0], state.point[1] + 1))
    if command in {"end", "endram", "returnram", "gotobeatenscript"}:
        return []
    if command in {"return", "gotopostbattlescript"}:
        return [replace(after, point=state.stack[-1], stack=state.stack[:-1])] if state.stack else []
    if command.startswith("trainerbattle"):
        return _battle_edges(after, instruction, scripts)
    if command in {"goto", "call", "vgoto", "vcall"}:
        return [_jump(after, scripts.target(args[0]), command in {"call", "vcall"})]
    if "_if_" in command and command.startswith(("goto", "call", "vgoto")):
        return _branch(after, instruction, scripts)
    if command in {"setvar", "setorcopyvar", "copyvar"}:
        return [after.assigning(*args[:2])]
    if command in {"setflag", "clearflag"}:
        return [after.assigning(args[0], "TRUE" if command == "setflag" else "FALSE")]
    if command in {"compare", "compare_var_to_value", "compare_var_to_var"}:
        return [replace(after, comparison=(args[0], args[1]))]
    if command == "checkflag":
        return [replace(after, comparison=(args[0], "TRUE"))]
    if command == "switch":
        return [replace(after, comparison=(args[0], ""))]
    if command == "case":
        if not state.comparison:
            raise ValueError(f"{instruction.source} : case sans switch")
        branch = Instruction("goto_if_eq", (state.comparison[0], *args), instruction.source)
        return _branch(after, branch, scripts)
    if command in {"random", "addvar", "subvar"}:
        return [_arithmetic(after, instruction, scripts.constants)]
    if command in {"special", "specialvar"}:
        modified = scripts.writes.get(args[-1], frozenset()) | {args[0] if command == "specialvar" else "VAR_RESULT"}
        return [_invalidate(after, modified)]
    if command in _RESULT_WRITES:
        return [replace(after, values=tuple((key, value) for key, value in after.values if key != "VAR_RESULT"))]
    return [after]


def _invalidate(state: ScriptState, modified: frozenset[str]) -> ScriptState:
    # Sans interprétation du C, oublier une exigence peut élargir une offre, jamais la cacher à tort.
    return replace(
        state,
        values=tuple((key, value) for key, value in state.values if key not in modified),
        requirements=frozenset(
            requirement for requirement in state.requirements if requirement.subject not in modified
        ),
    )


_RESULT_WRITES = frozenset(
    {
        "special",
        "multichoice",
        "multichoicedefault",
        "yesnobox",
        "checkitem",
        "giveitem",
        "giveitem_msg",
        "additem",
        "finditem",
        "givemon",
        "giveegg",
        "checkitemspace",
        "checkmoney",
        "checkcoins",
        "givedecoration",
    }
)


def _arithmetic(state: ScriptState, instruction: Instruction, constants: dict[str, int]) -> ScriptState:
    command, args = instruction.command, instruction.args
    if command == "random":
        count = number_value(state.value(args[0]), constants)
        if count is None or not 1 <= count <= 65535:
            raise ValueError(f"{instruction.source} : borne aléatoire inconnue : {args[0]}")
        return state.assigning("VAR_RESULT", f"range:0:{count}")
    offset = number_value(state.value(args[1]), constants)
    if offset is None:
        raise ValueError(f"{instruction.source} : incrément inconnu : {args[1]}")
    value = shifted_value(state.value(args[0]), offset if command == "addvar" else -offset, constants)
    return state.assigning(args[0], value)


def script_states(scripts: Gen3Scripts, label: str) -> tuple[ScriptState, ...]:
    """Chaque contexte d'appel conserve ses variables ; aucun retour n'est relié à un autre appel."""
    pending = [ScriptState(scripts.target(label))]
    seen: set[ScriptState] = set()
    result: list[ScriptState] = []
    for _ in range(_MAX_STEPS):
        if not pending:
            return tuple(result)
        state = pending.pop()
        if state in seen:
            continue
        seen.add(state)
        instruction = scripts.instruction(state.point)
        if instruction is None:
            following = scripts.blocks[state.point[0]].following
            if following:
                pending.append(replace(state, point=scripts.target(following)))
            continue
        if instruction.command.startswith("."):
            raise ValueError(f"{instruction.source} : donnée exécutée comme un script : {instruction.command}")
        result.append(state)
        pending.extend(_next(state, instruction, scripts))
    raise ValueError(f"{label} : analyse de flot GBA trop longue")
