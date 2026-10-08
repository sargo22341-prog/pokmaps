"""Conditions des offres de la 2e génération, lues dans les scripts d'événements (offer_conditions).

Un script teste le moment (`checktime MORN`), le jour (`readvar VAR_WEEKDAY` puis `ifequal MONDAY`), un drapeau du
scénario (`checkevent`, `checkflag`) ou la version (`checkver`), puis branche (`iftrue`, `ifequal`…). Chaque ligne
est un point de l'analyse ; une branche ajoute à l'état ce qu'elle établit. Les autres tests (objet porté, argent,
réponse du joueur) ne disent pas quand l'offre existe : leurs branches gardent l'état tel quel.

La présence d'un personnage compte aussi : moments de son object_event, jours où un rappel de carte le fait
apparaître (`appear` / `disappear` selon VAR_WEEKDAY et checktime), et drapeau qui le cache une fois levé.
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass

from .offer_conditions import (
    ALL_TIMES,
    ALL_WEEKDAYS,
    ALWAYS,
    TIMES_OF_DAY,
    WEEKDAYS,
    Condition,
    solve,
    time_mask,
    weekday_mask,
)
from .pret_gen2_scripts import TERMINATORS, ScriptFile
from .pret_source import macro_args

_FLAG_CHECKS = frozenset({"checkevent", "checkflag"})
_FLAG_WRITES = frozenset({"setevent", "clearevent", "setflag", "clearflag"})
_APPEARANCE = frozenset({"appear", "disappear"})
# Commandes qui changent un drapeau ou la présence d'un objet (dont le drapeau change avec elle).
FLAG_WRITES = _FLAG_WRITES | _APPEARANCE
# Commandes qui rendent un objet visible : baisser son drapeau, ou le faire apparaître.
SHOWING = frozenset({"clearevent", "clearflag", "appear"})
_JUMPS = frozenset({"sjump", "farsjump"})
_CALLS = frozenset({"scall", "farscall"})
_STD_JUMP, _STD_CALL = "jumpstd", "callstd"
_TRAINER = "trainer"
_WEEKDAY_VAR = "VAR_WEEKDAY"
# Lignes déroulées au plus par rappel de carte et par couple jour × moment : les rappels de pret en ont quelques
# dizaines, sans boucle.
_MAX_STEPS = 10_000

# Ce que vient de tester le script : un drapeau, un moment, le jour ou la version.
_Subject = tuple[str, ...]
# Point d'un script : fichier, bloc (label), rang de la ligne dans le bloc.
Point = tuple[ScriptFile, str, int]
_Next = tuple[Hashable, Condition]


@dataclass(frozen=True)
class _Test:
    """Ce qu'établit une branche : drapeau levé ou non, moments, jours, ou résultat de checkver."""

    kind: str  # flag, times, weekdays, version
    flag: str = ""
    value: bool = False
    mask: int = 0


@dataclass(frozen=True)
class _Edge:
    point: Point
    test: _Test | None = None


class Gen2Conditions:
    """Lecteur des conditions d'un dépôt pret de la 2e génération (scripts communs de engine/events)."""

    def __init__(self, std_scripts: ScriptFile) -> None:
        self.std_scripts = std_scripts

    def script_conditions(self, script_file: ScriptFile, label: str, checkver: bool | None) -> dict[Point, Condition]:
        """Condition certaine à chaque ligne atteignable depuis `label` (version résolue par `checkver`)."""

        def transfer(point: Hashable, condition: Condition) -> list[_Next]:
            return self._transfer(point, condition, checkver)

        entry: Point = (script_file, label, 0)
        points = solve([(entry, ALWAYS)], transfer)
        return {_point(point): condition for point, condition in points.items()}

    def own_flags(self, points: dict[Point, Condition]) -> frozenset[str]:
        """Drapeaux que le script lève ou baisse lui-même (« déjà donné », dresseur battu), et objets qu'il fait
        apparaître ou disparaître (constantes de object_const_def) : ils disent ce que le personnage a déjà fait,
        pas quand son offre devient possible."""
        flags = set()
        for script_file, block, index in points:
            line = _line(script_file, block, index)
            if line is None:
                continue
            command = line.split()[0]
            if command in FLAG_WRITES:
                flags.add(line.split()[1])
            elif command == _TRAINER:
                flags.add(macro_args(line, _TRAINER)[2])
        return frozenset(flags)

    def _transfer(self, point: Hashable, condition: Condition, checkver: bool | None) -> list[_Next]:
        result: list[_Next] = []
        for edge in self.edges(*_point(point)):
            refined = _apply(condition, edge.test, checkver)
            if refined is not None:
                result.append((edge.point, refined))
        return result

    def edges(self, script_file: ScriptFile, block: str, index: int) -> list[_Edge]:
        """Points où l'exécution continue après la ligne, avec ce qu'établit chaque branche."""
        line = _line(script_file, block, index)
        if line is None:
            following = script_file.blocks[block].following
            return [_Edge((script_file, following, 0))] if following else []
        command = line.split()[0]
        after = _Edge((script_file, block, index + 1))
        target = _local_target(script_file, block, line, command)
        if command in _JUMPS:
            return [_Edge((script_file, target, 0))] if target else []
        if command in _CALLS or command == _TRAINER:
            return [after, *([_Edge((script_file, target, 0))] if target else [])]
        if command in (_STD_JUMP, _STD_CALL):
            std = self._std_edge(line)
            return std if command == _STD_JUMP else [after, *std]
        if command in TERMINATORS:
            return []
        if command in _BRANCHES:
            return _branch_edges(script_file, block, index, line, command, target, after)
        return [after]

    def _std_edge(self, line: str) -> list[_Edge]:
        name = line.split()[1]
        return [_Edge((self.std_scripts, name, 0))] if self.std_scripts.has_label(name) else []


def _point(point: Hashable) -> Point:
    if not (isinstance(point, tuple) and len(point) == 3 and isinstance(point[0], ScriptFile)):
        raise TypeError(f"Point de script inattendu : {point!r}")
    return point


def _line(script_file: ScriptFile, block: str, index: int) -> str | None:
    lines = script_file.blocks[block].lines
    return lines[index] if index < len(lines) else None


def _local_target(script_file: ScriptFile, block: str, line: str, command: str) -> str | None:
    """Label du fichier vers lequel saute la ligne (« .Local » est relatif au label global courant)."""
    if command not in _BRANCHES and command not in _JUMPS and command not in _CALLS and command != _TRAINER:
        return None
    reference = macro_args(line, command)[-1]
    if reference.startswith("."):
        reference = f"{block.split('.')[0]}{reference}"
    return reference if script_file.has_label(reference) else None


_BRANCHES = frozenset({"iftrue", "iffalse", "ifequal", "ifnotequal", "ifgreater", "ifless"})


def _branch_edges(
    script_file: ScriptFile, block: str, index: int, line: str, command: str, target: str | None, after: _Edge
) -> list[_Edge]:
    """Branche : la cible et la suite, chacune avec ce qu'elle établit sur ce que le script vient de tester."""
    subject = _subject_before(script_file, block, index)
    taken, skipped = _branch_tests(subject, command, macro_args(line, command)[:-1])
    edges = [_Edge(after.point, skipped)]
    if target:
        edges.append(_Edge((script_file, target, 0), taken))
    return edges


def _branch_tests(subject: _Subject | None, command: str, args: list[str]) -> tuple[_Test | None, _Test | None]:
    """Ce qu'établissent la branche prise et la suite, pour le sujet testé (None : rien de suivi)."""
    if subject is None:
        return None, None
    if command in ("iftrue", "iffalse"):
        jump_if = command == "iftrue"
        match subject[0]:
            case "flag":
                return _Test("flag", subject[1], jump_if), _Test("flag", subject[1], not jump_if)
            case "time":
                mask = int(subject[1])
                inside, outside = _Test("times", mask=mask), _Test("times", mask=ALL_TIMES & ~mask)
                return (inside, outside) if jump_if else (outside, inside)
            case "version":
                return _Test("version", value=jump_if), _Test("version", value=not jump_if)
        return None, None
    if subject[0] == "weekday" and command in ("ifequal", "ifnotequal"):
        day = weekday_mask(args[0])
        same, other = _Test("weekdays", mask=day), _Test("weekdays", mask=ALL_WEEKDAYS & ~day)
        return (same, other) if command == "ifequal" else (other, same)
    return None, None


def _subject_before(script_file: ScriptFile, block: str, index: int) -> _Subject | None:
    """Ce que teste la dernière commande de test avant la ligne, dans le même bloc (les branches successives d'un
    même `readvar` le relisent). Une commande qui n'est ni un test suivi ni une branche efface le sujet."""
    subject = None
    for line in script_file.blocks[block].lines[:index]:
        subject = _next_subject(line, subject)
    return subject


def _next_subject(line: str, subject: _Subject | None) -> _Subject | None:
    parts = line.split()
    command = parts[0]
    if command in _FLAG_CHECKS:
        return ("flag", parts[1])
    if command == "checktime":
        return ("time", str(time_mask({parts[1]})))
    if command == "checkver":
        return ("version",)
    if command == "readvar":
        return ("weekday",) if parts[1] == _WEEKDAY_VAR else None
    return subject if command in _BRANCHES else None


def _apply(condition: Condition, test: _Test | None, checkver: bool | None) -> Condition | None:
    """État après une branche, None si elle ne peut pas être prise (autre version, moment ou jour impossible)."""
    if test is None:
        return condition
    match test.kind:
        case "flag":
            refined = condition.requiring(test.flag, test.value)
        case "times":
            refined = condition.with_times(test.mask)
        case "weekdays":
            refined = condition.with_weekdays(test.mask)
        case "version":
            return condition if checkver is None or test.value == checkver else None
        case _:
            raise ValueError(f"Test de branche inconnu : {test}")
    return refined if refined.possible else None


@dataclass(frozen=True)
class _Path:
    """Fin d'un chemin d'un rappel de carte : ce qu'il exige, et la dernière action sur chaque objet (vrai :
    appear)."""

    condition: Condition
    actions: dict[str, bool]


def object_appearance(
    reader: Gen2Conditions, script_file: ScriptFile, persistent: frozenset[str]
) -> dict[str, Condition]:
    """Ce qu'exige la présence des objets que les rappels de la carte montrent ou cachent (constantes de
    object_const_def), quand elle dépend du jour, du moment ou du scénario.

    Chaque rappel est déroulé pour chacun des 21 couples jour × moment ; un drapeau testé garde ses deux branches et
    devient une exigence du chemin. Un chemin laisse l'objet visible s'il finit par `appear`, ou s'il n'y touche pas
    alors que l'objet peut déjà être visible (`persistent` : drapeau baissé au départ, ou changé par une scène).
    La présence exige ce qu'exigent tous les chemins qui la laissent visible : une condition nécessaire, jamais plus
    stricte que le jeu. Un objet que les rappels cachent toujours n'a pas de condition ici : une scène le montre."""
    paths = {
        label: [
            path
            for time in range(len(TIMES_OF_DAY))
            for day in range(len(WEEKDAYS))
            for path in _callback_paths(reader, script_file, label, Condition(times=1 << time, weekdays=1 << day))
        ]
        for label in object_callbacks(script_file)
    }
    result = {}
    for const, label in _touching_callback(script_file, paths).items():
        visible = [path.condition for path in paths[label] if path.actions.get(const, const in persistent)]
        if not visible:
            continue
        condition = visible[0]
        for other in visible[1:]:
            condition = condition.join(other)
        if condition != ALWAYS:
            result[const] = condition
    return result


def _touching_callback(script_file: ScriptFile, paths: dict[str, list[_Path]]) -> dict[str, str]:
    """Objet -> le rappel qui le montre ou le cache. Tous les rappels s'exécutent au chargement de la carte : un
    objet que deux rappels touchent demanderait de les composer, ce que pret ne fait pas ; la lecture s'arrête."""
    result: dict[str, str] = {}
    for label, label_paths in paths.items():
        for const in sorted({const for path in label_paths for const in path.actions}):
            if const in result:
                raise ValueError(f"{script_file.path.name} : {const} montré ou caché par {result[const]} et {label}")
            result[const] = label
    return result


def object_callbacks(script_file: ScriptFile) -> list[str]:
    """Labels des rappels de la carte qui font apparaître ou disparaître des objets."""
    labels = []
    for block in script_file.blocks.values():
        for line in block.lines:
            if line.startswith("callback "):
                label = macro_args(line, "callback")[1]
                if script_file.has_label(label) and _has_appearance(script_file, label):
                    labels.append(label)
    return labels


def _has_appearance(script_file: ScriptFile, label: str) -> bool:
    return any(line.split()[0] in _APPEARANCE for line in script_file.reachable_lines(label, None))


def _callback_paths(reader: Gen2Conditions, script_file: ScriptFile, label: str, start: Condition) -> list[_Path]:
    """Chemins du rappel à partir de `start` (un seul moment, un seul jour), avec leur dernière action par objet."""
    paths: list[_Path] = []
    stack: list[tuple[Point, Condition, dict[str, bool]]] = [((script_file, label, 0), start, {})]
    for _ in range(_MAX_STEPS):
        if not stack:
            return paths
        point, condition, actions = stack.pop()
        line = _line(*point)
        if line is not None and line.split()[0] in _APPEARANCE:
            actions = {**actions, line.split()[1]: line.split()[0] == "appear"}
        edges = reader.edges(*point)
        if not edges:
            paths.append(_Path(condition, actions))
        for edge in edges:
            refined = _apply(condition, edge.test, None)
            if refined is not None:
                stack.append((edge.point, refined, actions))
    raise ValueError(f"{script_file.path.name} : rappel {label} trop long à dérouler")
