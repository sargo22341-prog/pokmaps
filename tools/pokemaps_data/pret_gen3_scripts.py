"""Index borné des scripts GBA, sélectionné pour une version du jeu."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_script_effects import special_writes
from .pret_gen3_script_values import script_constants

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo

_MAX_LABELS = 40_000
_MAX_LINES = 500_000
_LABEL = re.compile(r"^(\w+)::?\s*$")


@dataclass(frozen=True)
class Instruction:
    command: str
    args: tuple[str, ...]
    source: str


@dataclass(frozen=True)
class ScriptBlock:
    lines: tuple[Instruction, ...]
    following: str | None


def parse_scripts(text: str, source: str, predefined: dict[str, str] | None = None) -> dict[str, ScriptBlock]:
    """Les données (textes, mouvements et boutiques) gardent leur label, sans devenir exécutables."""
    aliases = (predefined or {}) | dict(re.findall(r"^\s*\.(?:equ|set)\s+(\w+),\s*([A-Z_]\w*)\s*$", text, re.M))
    for name, value in aliases.items():
        text = re.sub(r"\b" + name + r"\b", value, text)
    bodies: dict[str, list[Instruction]] = {}
    names: list[str] = []
    count = 0
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("@", 1)[0].strip()
        if match := _LABEL.fullmatch(line):
            label = match[1]
            if label in bodies or len(names) >= _MAX_LABELS:
                raise ValueError(f"{source}:{number} : label répété ou trop nombreux : {label}")
            names.append(label)
            bodies[label] = []
        elif line and names:
            parts = line.split(None, 1)
            args = _arguments(parts[1]) if len(parts) == 2 else ()
            bodies[names[-1]].append(Instruction(parts[0], args, f"{source}:{number}"))
            count += 1
            if count > _MAX_LINES:
                raise ValueError(f"{source} : trop de lignes de scripts")
    return {
        label: ScriptBlock(tuple(bodies[label]), names[index + 1] if index + 1 < len(names) else None)
        for index, label in enumerate(names)
    }


def _arguments(text: str) -> tuple[str, ...]:
    parts = [part.strip() for part in text.split(",")]
    # Les macros GAS acceptent aussi un espace comme séparateur ; garder les expressions parenthésées.
    return tuple(token for part in parts for token in ([part] if "(" in part or '"' in part else part.split()))


class Gen3Scripts:
    def __init__(
        self, blocks: dict[str, ScriptBlock], constants: dict[str, int], writes: dict[str, frozenset[str]] | None = None
    ) -> None:
        self.blocks = blocks
        self.constants = constants
        self.writes = writes or {}

    @classmethod
    def from_repo(cls, repo: Gen3PretRepo, version: str) -> Gen3Scripts:
        result = cls({}, script_constants(repo.root), special_writes(repo.root))
        predefined = {}
        if repo.ruby:
            text = repo.source_text("constants/version.inc", version)
            predefined = dict(re.findall(r"^\s*\.set\s+(\w+),\s*(\w+)\s*$", text, re.M))
        paths = sorted((repo.root / "data/maps").glob("*/scripts.inc"))
        paths += sorted((repo.root / "data/scripts").glob("*.inc"))
        paths += [repo.root / "data/event_scripts.s"]
        paths += [
            repo.root / relative
            for relative in re.findall(
                r'\.include "(data/[^"/]+\.inc)"', repo.source_text("data/event_scripts.s", version)
            )
            if "scripts" in relative and "script_cmd_table" not in relative
        ]
        for path in paths:
            relative = path.relative_to(repo.root).as_posix()
            text = repo.source_text(relative, version)
            for name, value in re.findall(r"^\s*\.set\s+(\w+),\s*(\d+)\s*$", text, re.M):
                if name in result.constants and result.constants[name] != int(value):
                    raise ValueError(f"{relative} : constante de script ambiguë : {name}")
                result.constants[name] = int(value)
            blocks = parse_scripts(text, relative, predefined)
            if duplicate := result.blocks.keys() & blocks.keys():
                raise ValueError(f"{relative} : labels répétés : {sorted(duplicate)}")
            result.blocks.update(blocks)
            if len(result.blocks) > _MAX_LABELS:
                raise ValueError(f"{repo.root} : trop de labels de scripts")
        return result

    def instruction(self, point: tuple[str, int]) -> Instruction | None:
        label, index = point
        if label not in self.blocks:
            raise ValueError(f"Script GBA absent : {label}")
        block = self.blocks[label]
        return block.lines[index] if index < len(block.lines) else None

    def target(self, label: str) -> tuple[str, int]:
        if label not in self.blocks:
            raise ValueError(f"Script GBA absent : {label}")
        return label, 0
