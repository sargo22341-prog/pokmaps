"""Table des commandes de script de Diamant/Perle et forme de leurs arguments, lues dans les sources du moteur.

gScriptCmdTable (arm9/asm/unk_02038C78.s) donne la fonction de chaque opcode. La forme des arguments se lit
dans le corps de la fonction : ScriptReadByte (1 octet), ScriptReadHalfword, ScriptGetVar et
ScriptGetVarPointer (2), ScriptReadWord (4), dans l'ordre du code. Un mot ajouté à ctx->scriptPtr est une
adresse relative : saut (ScriptJump), appel (ScriptCall) ou données (mouvements). Une lecture sous condition
n'est admise que dans deux formes relevées dans le moteur : boucle de longueur fixe et switch sur un premier
argument ; toute autre forme laisse la commande « illisible », et son emploi dans un script arrête la lecture.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from itertools import pairwise
from pathlib import Path

from .pret_gen4_source import read_text

_TABLE_FILE = "arm9/asm/unk_02038C78.s"
_TABLE_SIZE = 721
_READS = {
    "ScriptReadByte": (1, "value"),
    "ScriptReadHalfword": (2, "value"),
    "ScriptGetVar": (2, "var"),
    "ScriptGetVarPointer": (2, "pointer"),
    "ScriptReadWord": (4, "value"),
}
# Fonctions recevant le contexte sans lire d'argument : contrôle du script et marqueur de paramètre inutilisé.
_NO_READ = frozenset({"SetupNativeScript", "ScriptJump", "ScriptCall", "ScriptReturn", "StopScript", "unused"})
_FUNCTION = re.compile(
    r"^(?:static\s+)?(?:BOOL|u32|bool8|s32|void|u8|u16)\s+(\w+)\s*\(\s*(?:struct\s+)?ScriptContext\s*\*\s*(\w+)[^)]*\)\s*\{",
    re.MULTILINE,
)
_COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
# Les fonctions non décompilées gardent leur assembleur après #else (NONMATCHING) : seule la version C est lue.
_NONMATCHING_ASM = re.compile(r"#else\s*\n(?://[^\n]*\n)?asm .*?#endif", re.DOTALL)
_ASM_FUNCTION = re.compile(r"\tthumb_func_start (\w+)\n")
_ASM_BRANCH = re.compile(r"^b(?:eq|ne|lt|gt|le|ge|hi|lo|hs|ls|cc|cs|mi|pl)?\s+_")
_MAX_HELPER_DEPTH = 3
_STORES_VAR = re.compile(r"(?<!\w)GetVarPointer\s*\(|->data\[\d+\]\s*=")


@dataclass(frozen=True)
class Argument:
    size: int
    # value, var (numéro de variable ou valeur, lu), pointer (variable que la commande peut écrire), jump, call, data
    role: str


@dataclass(frozen=True)
class ScriptCommand:
    opcode: int
    name: str
    arguments: tuple[Argument, ...]
    # Forme variable : selon la valeur du premier argument, arguments supplémentaires (switch du moteur).
    cases: tuple[tuple[int, tuple[Argument, ...]], ...]
    ends: bool  # End, Return ou saut inconditionnel : le flux ne continue pas après la commande
    problem: str | None  # raison pour laquelle la forme n'a pas pu être lue
    # La fonction garde un numéro de variable lu par valeur pour l'écrire (GetVarPointer, ctx->data[n] = …) :
    # un argument qui désigne une variable peut alors être écrit, même lu par ScriptReadHalfword.
    stores_var: bool = False


def read_command_table(root: Path) -> tuple[ScriptCommand, ...]:
    names = _table_names(root)
    functions = _c_functions(root)
    assembly = _asm_functions(root)
    commands = []
    for opcode, name in enumerate(names):
        if name in functions:
            command = _c_command(opcode, name, functions, assembly)
            commands.append(replace(command, stores_var=bool(_STORES_VAR.search(functions[name][0]))))
        elif name in assembly:
            command = _asm_command(opcode, name, assembly[name])
            commands.append(replace(command, stores_var="bl GetVarPointer" in assembly[name]))
        else:
            commands.append(ScriptCommand(opcode, name, (), (), False, "fonction introuvable"))
    return tuple(commands)


def _table_names(root: Path) -> list[str]:
    text = read_text(root / _TABLE_FILE)
    start = text.index("gScriptCmdTable:")
    names = re.findall(r"\.word (\w+)", text[start:])[:_TABLE_SIZE]
    if len(names) != _TABLE_SIZE or f".word {_TABLE_SIZE} ; NELEMS(gScriptCmdTable)" not in text:
        raise ValueError(f"{root / _TABLE_FILE} : table de {len(names)} commandes, {_TABLE_SIZE} attendues")
    return names


def _c_functions(root: Path) -> dict[str, tuple[str, str]]:
    """Corps des fonctions C qui reçoivent le contexte de script : nom -> (corps, nom du paramètre)."""
    functions: dict[str, tuple[str, str]] = {}
    for path in sorted((root / "arm9/src").glob("*.c")):
        text = _COMMENTS.sub("", _NONMATCHING_ASM.sub("", read_text(path)))
        for match in _FUNCTION.finditer(text):
            functions.setdefault(match.group(1), (_braced(text, match.end()), match.group(2)))
    return functions


def _braced(text: str, start: int) -> str:
    depth, position = 1, start
    while depth:
        if position >= len(text):
            raise ValueError("fonction C sans accolade fermante")
        depth += {"{": 1, "}": -1}.get(text[position], 0)
        position += 1
    return text[start : position - 1]


def _asm_functions(root: Path) -> dict[str, str]:
    functions: dict[str, str] = {}
    for path in sorted((root / "arm9").rglob("*.s")):
        parts = _ASM_FUNCTION.split(read_text(path))
        functions.update(zip(parts[1::2], parts[2::2], strict=True))
    return functions


def _asm_command(opcode: int, name: str, body: str) -> ScriptCommand:
    """Fonction en assembleur : lectures linéaires, ou premier mot lu puis aiguillage (table de sauts « case k »
    ou suite de cmp/beq) dont chaque cas lit ses arguments avant tout branchement."""
    lines = [
        raw.strip() if raw.strip().startswith(".short") else raw.split(";")[0].strip() for raw in body.splitlines()
    ]
    # Registres qui portent le contexte : r0 à l'entrée, et ses copies « add rX, r0, #0x0 ».
    context = {"r0"} | {m.group(1) for line in lines[:4] if (m := re.match(r"^add (r\d), r0, #0x0$", line))}
    try:
        first_branch = next(
            (i for i, line in enumerate(lines) if _ASM_BRANCH.match(line) or line == "add pc, r0"), None
        )
        head = _asm_reads(lines[:first_branch], context)
        if first_branch is None or not _asm_reads(lines[first_branch:], context):
            return ScriptCommand(opcode, name, tuple(head), (), False, None)
        return ScriptCommand(opcode, name, tuple(head), _asm_switch(lines, head, context), False, None)
    except _Unreadable as reason:
        return ScriptCommand(opcode, name, (), (), False, str(reason))


def _asm_switch(
    lines: list[str], head: list[Argument], context: set[str]
) -> tuple[tuple[int, tuple[Argument, ...]], ...]:
    labels = {line[:-1]: i for i, line in enumerate(lines) if re.match(r"^_\w+:$", line)}
    cases = _asm_cases(lines)
    if [argument.size for argument in head] != [2] or not cases or set(cases.values()) - labels.keys():
        raise _Unreadable("lecture en assembleur non linéaire")
    arguments = []
    for value, label in sorted(cases.items()):
        case = _until_end(lines[labels[label] + 1 :])
        branch = next((i for i, line in enumerate(case) if _ASM_BRANCH.match(line)), len(case))
        if _asm_reads(case[branch:], context):
            raise _Unreadable("lecture conditionnelle en assembleur")
        arguments.append((value, tuple(_asm_reads(case[:branch], context))))
    return tuple(arguments)


def _asm_reads(lines: list[str], context: set[str]) -> list[Argument]:
    """Lectures dans l'ordre : appels ScriptRead*, ou octet lu en avançant ctx->scriptPtr (str d'un pointeur
    incrémenté de 1 à l'offset 0x8 du contexte)."""
    reads = []
    for previous, line in zip(["", *lines], lines, strict=False):
        call = re.match(r"^bl (ScriptRead\w+)$", line)
        if call:
            if call.group(1) not in _READS:
                raise _Unreadable(f"lecture de script inconnue : {call.group(1)}")
            reads.append(Argument(*_READS[call.group(1)]))
        store = re.match(r"^str (r\d), \[(r\d), #0x8\]$", line)
        if store and store.group(2) in context:
            if not re.match(rf"^add {store.group(1)}, r\d, #0x1$", previous):
                raise _Unreadable("pointeur de script modifié en assembleur")
            reads.append(Argument(1, "value"))
    return reads


def _until_end(lines: list[str]) -> list[str]:
    for index, line in enumerate(lines):
        if line.startswith(("b _", "pop ")):
            return lines[:index]
    return lines


def _asm_cases(lines: list[str]) -> dict[int, str]:
    """Valeur -> label, d'après une table de sauts commentée « case k » ou des paires cmp r0, #k / beq."""
    cases = {}
    for line in lines:
        entry = re.match(r"^\.short (_\w+) - _\w+ - 2; case (\d+)$", line)
        if entry:
            cases[int(entry.group(2))] = entry.group(1)
    for compare, branch in pairwise(lines):
        value = re.match(r"^cmp r0, #(0x[0-9a-fA-F]+|\d+)$", compare)
        target = re.match(r"^beq (_\w+)$", branch)
        if value and target:
            cases[int(value.group(1), 0)] = target.group(1)
    return cases


def _c_command(
    opcode: int, name: str, functions: dict[str, tuple[str, str]], assembly: dict[str, str]
) -> ScriptCommand:
    body, context = functions[name]
    try:
        arguments, cases = _layout(body, context, functions, assembly, 0)
    except _Unreadable as reason:
        return ScriptCommand(opcode, name, (), (), False, str(reason))
    return ScriptCommand(opcode, name, arguments, cases, _ends(body, context), None)


class _Unreadable(Exception):
    pass


def _layout(
    body: str, context: str, functions: dict[str, tuple[str, str]], assembly: dict[str, str], depth: int
) -> tuple[tuple[Argument, ...], tuple[tuple[int, tuple[Argument, ...]], ...]]:
    if loop := _fixed_loop(body, context):
        return loop, ()
    arguments: list[Argument] = []
    switch = _switch(body, context)
    for nesting, function, position in _calls(body, context):
        if function in _READS:
            if nesting and not (switch and switch[0] <= position):
                raise _Unreadable(f"lecture conditionnelle ({function})")
            if not nesting:
                arguments.append(Argument(*_READS[function]))
        elif function not in _NO_READ:
            arguments.extend(_helper(function, nesting, functions, assembly, depth))
    words = [i for i, argument in enumerate(arguments) if argument.size == 4]
    roles = _word_roles(body, context)
    if len(roles) > len(words):
        raise _Unreadable("adresse relative sans mot lu")
    for index, role in zip(words, roles, strict=False):
        arguments[index] = Argument(4, role)
    if switch:
        return tuple(arguments), switch[1]
    return tuple(arguments), ()


def _calls(body: str, context: str) -> list[tuple[int, str, int]]:
    """(profondeur d'accolades, fonction, position) des appels qui reçoivent le contexte."""
    found = []
    nesting = 0
    pattern = re.compile(r"[{}]|\b(\w+)\s*\(\s*" + re.escape(context) + r"\s*[,)]")
    for match in pattern.finditer(body):
        if match.group(0) == "{":
            nesting += 1
        elif match.group(0) == "}":
            nesting -= 1
        else:
            found.append((nesting, match.group(1), match.start()))
    return found


def _helper(
    function: str, nesting: int, functions: dict[str, tuple[str, str]], assembly: dict[str, str], depth: int
) -> tuple[Argument, ...]:
    if function in functions and depth < _MAX_HELPER_DEPTH:
        body, context = functions[function]
        arguments, cases = _layout(body, context, functions, assembly, depth + 1)
        if cases or (arguments and nesting):
            raise _Unreadable(f"lecture conditionnelle dans {function}")
        return arguments
    if function in assembly and "bl ScriptRead" not in assembly[function]:
        return ()
    raise _Unreadable(f"fonction appelée illisible : {function}")


_LOOP = re.compile(r"for \(s32 (\w+) = 0; \1 < (\d+); \1\+\+\) \{\s*\w+\[\1\] = (ScriptRead\w+)\(\w+\);\s*\}")


def _fixed_loop(body: str, context: str) -> tuple[Argument, ...] | None:
    """Boucle `for (i = 0; i < N; i++) tableau[i] = ScriptReadX(ctx);` entourée de lectures linéaires."""
    match = _LOOP.search(body)
    if match is None:
        return None
    before = [Argument(*_READS[f]) for n, f, p in _calls(body[: match.start()], context) if f in _READS and not n]
    after = [Argument(*_READS[f]) for n, f, p in _calls(body[match.end() :], context) if f in _READS and not n]
    repeated = [Argument(*_READS[match.group(3)])] * int(match.group(2))
    return (*before, *repeated, *after)


_SWITCH = re.compile(r"(\w+)\s*=\s*(ScriptRead\w+)\(\s*(\w+)\s*\);.*?switch \((\w+)\) \{", re.DOTALL)
_CASE = re.compile(r"case (\d+):")


def _switch(body: str, context: str) -> tuple[int, tuple[tuple[int, tuple[Argument, ...]], ...]] | None:
    """switch sur le premier argument lu : arguments supplémentaires de chaque cas, lus dans son bloc."""
    match = _SWITCH.search(body)
    if match is None or match.group(1) != match.group(4) or match.group(3) != context:
        return None
    block = _braced(body, match.end())
    labels = list(_CASE.finditer(block))
    cases = []
    for label, following in zip(labels, [*labels[1:], None], strict=True):
        section = block[label.end() : following.start() if following else len(block)]
        reads = [Argument(*_READS[f]) for _, f, _ in _calls(section, context) if f in _READS]
        cases.append((int(label.group(1)), tuple(reads)))
    default = block[block.find("default:") :] if "default:" in block else ""
    if any(f in _READS for _, f, _ in _calls(default, context)):
        raise _Unreadable("lecture dans le cas par défaut")
    return match.end(), tuple(cases)


def _word_roles(body: str, context: str) -> list[str]:
    """Rôle des mots lus ajoutés à ctx->scriptPtr, dans l'ordre : saut, appel ou données."""
    if f"{context}->scriptPtr" not in body.replace(" ", ""):
        return []
    if "ScriptJump(" in body:
        return ["jump"]
    if "ScriptCall(" in body:
        return ["call"]
    return ["data"]


def _ends(body: str, context: str) -> bool:
    """End, Return et saut inconditionnel (appelé hors de tout bloc) arrêtent le flux linéaire."""
    for nesting, function, _ in _calls(body, context):
        if function in {"StopScript", "ScriptReturn", "ScriptJump"} and nesting == 0:
            return True
    return False
