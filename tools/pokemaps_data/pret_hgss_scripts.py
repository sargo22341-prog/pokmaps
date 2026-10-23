"""Scripts textuels HGSS : instructions et graphe conservés sans aplatir les conditions."""

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .pret_gen4_source import read_text


@dataclass(frozen=True)
class Instruction:
    line: int
    command: str
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class Script:
    source: str
    entries: tuple[str, ...]
    labels: dict[str, int]
    steps: tuple[Instruction, ...]


def read_script(path: Path, root: Path) -> Script:
    entries, labels, steps = [], {}, []
    for number, raw in enumerate(read_text(path).splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line or line.startswith(("#", ".")):
            continue
        if re.fullmatch(r"\w+:", line):
            label = line[:-1]
            if label in labels:
                raise ValueError(f"{path}:{number} : étiquette répétée : {label}")
            labels[label] = len(steps)
            continue
        command, _, arguments = line.partition(" ")
        if command == "ScrDef":
            entries.append(arguments)
        elif command != "ScrDefEnd":
            steps.append(
                Instruction(number, command, tuple(a.strip() for a in arguments.split(",")) if arguments else ())
            )
    if len(steps) > 20000 or set(entries) - set(labels) or (not entries and steps):
        raise ValueError(f"{path} : entrées absentes ou script hors limite")
    for step in steps:
        branch = step.command in {"GoTo", "Call"} or step.command.startswith(("GoToIf", "CallIf"))
        if branch and (not step.arguments or step.arguments[-1] not in labels):
            raise ValueError(f"{path}:{step.line} : destination de script inconnue")
    return Script(path.relative_to(root).as_posix(), tuple(entries), labels, tuple(steps))


def read_scripts(root: Path) -> dict[int, Script]:
    paths = sorted((root / "files/fielddata/script/scr_seq").glob("*.s"))
    if len(paths) != 965:
        raise ValueError(f"HGSS : 965 scripts attendus, {len(paths)} lus")
    return {int(path.stem.split("_")[2]): read_script(path, root) for path in paths if not path.stem.endswith("_hdr")}


def reachable(script: Script, entry: str) -> set[int]:
    """Accessibilité structurelle ; les branches ne prouvent pas la disponibilité en jeu."""
    if entry not in script.labels:
        raise ValueError(f"{script.source} : entrée inconnue : {entry}")
    pending = [script.labels[entry]]
    visited: set[int] = set()
    for _ in range(60000):
        if not pending:
            return visited
        index = pending.pop()
        if index in visited or index == len(script.steps):
            continue
        if not 0 <= index < len(script.steps):
            raise ValueError(f"{script.source} : instruction hors limite : {index}")
        visited.add(index)
        step = script.steps[index]
        if step.command.startswith(("GoTo", "Call")) and step.arguments[-1] in script.labels:
            pending.append(script.labels[step.arguments[-1]])
        if step.command not in {"End", "Return", "GoTo", "GoToStd", "RestartCurrentScript"}:
            pending.append(index + 1)
    raise ValueError(f"{script.source} : parcours du graphe hors limite")


def script_payload(script: Script) -> dict:
    return dict(
        source=script.source,
        entries=script.entries,
        labels=script.labels,
        instructions=[asdict(step) for step in script.steps],
    )


def battle_sites(scripts: dict[int, Script], trainers: dict[str, int]) -> list[dict]:
    result = []
    for bank, script in scripts.items():
        for index, step in enumerate(script.steps):
            if step.command not in {"TrainerBattle", "MultiBattle", "RocketTrapBattle"}:
                continue
            resolved = [trainers[value] for value in step.arguments if value.startswith("TRAINER_")]
            variables = [value for value in step.arguments if value.startswith("VAR_")]
            partner = resolved[0] if step.command == "MultiBattle" else None
            result.append(
                dict(
                    bank=bank,
                    instruction=index,
                    source=script.source,
                    line=step.line,
                    command=step.command,
                    arguments=step.arguments,
                    trainers=resolved,
                    variables=variables,
                    opponents=resolved[1:] if partner is not None else resolved,
                    partner=partner,
                    entries=[entry for entry in script.entries if index in reachable(script, entry)],
                )
            )
    return result
