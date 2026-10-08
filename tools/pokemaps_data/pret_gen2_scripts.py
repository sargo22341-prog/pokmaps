"""Scripts d'événements de la 2e génération (maps/<Carte>.asm) : ce qu'exécute un script, version par version.

Un fichier de carte est découpé en blocs, un par label (global « Script: » ou local « .Suite: », nommé
« Script.Suite »). Lire un script revient à parcourir les blocs atteignables depuis son label : les sauts
(sjump, scall), les branches conditionnelles (iftrue, ifequal…) et la suite du fichier quand le bloc ne se
termine pas. Une condition sur un événement du scénario garde les deux branches : on veut tout ce que le
personnage peut faire. Seul `checkver` (Or ou Argent) est résolu, pour lire ce qui est propre à une version.

Le parcours est borné par le nombre de blocs du fichier : chaque bloc est visité une fois au plus.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .pret_source import macro_args, parse_int, source_lines

_LABEL = re.compile(r"^(\.?[A-Za-z_]\w*):{1,2}$")
_CONSTANT = re.compile(r"^DEF (\w+)\s+EQU\s+(\$[0-9A-Fa-f]+|\d+)$")
# Commandes après lesquelles l'exécution ne continue pas dans le bloc suivant du fichier. fruittree et
# describedecoration passent la main à un script du moteur (ScriptJump dans engine/overworld/scripting.asm) ;
# itemball et hiddenitem sont des données lues par le moteur, pas des commandes.
_TERMINATORS = frozenset(
    {
        "end",
        "fruittree",
        "describedecoration",
        "itemball",
        "hiddenitem",
        "sjump",
        "farsjump",
        "jumptext",
        "jumptextfaceplayer",
        "jumpstd",
        "endcallback",
        "return",
        "done",
        "text_end",
        "prompt",
        "step_end",
    }
)
# Commandes qui sautent vers un label (le dernier argument) ; seuls les labels du fichier sont suivis.
_JUMPS = frozenset({"sjump", "scall", "farsjump", "farscall"})
_BRANCHES = frozenset({"iftrue", "iffalse", "ifequal", "ifnotequal", "ifgreater", "ifless"})
# Script exécuté après la victoire contre un dresseur : dernier argument de la macro `trainer`.
_TRAINER = "trainer"
_CHECKVER = "checkver"
# Directives d'assemblage conditionnel : les fichiers de scripts d'Or et d'Argent n'en ont pas, et les lire sans
# choisir de branche mélangerait les versions.
_CONDITIONALS = frozenset({"IF", "ELIF", "ELSE", "ENDC"})


def check_unconditional(line: str, path: Path) -> None:
    """Arrête la lecture sur une directive d'assemblage conditionnel, que ce lecteur ne résout pas."""
    if line.split(maxsplit=1)[0].upper() in _CONDITIONALS:
        raise ValueError(f"{path.name} : condition d'assemblage non prise en charge dans un script : {line}")


@dataclass(frozen=True)
class _Block:
    lines: tuple[str, ...]
    following: str | None  # bloc suivant du fichier, si l'exécution peut y continuer


class ScriptFile:
    """Blocs de script d'un fichier de carte, et lignes atteignables depuis un label."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @cached_property
    def blocks(self) -> dict[str, _Block]:
        names: list[str] = []
        lines: dict[str, list[str]] = {}
        current_global = ""
        for line in source_lines(self.path):
            check_unconditional(line, self.path)
            match = _LABEL.match(line)
            if match is None:
                if names:
                    lines[names[-1]].append(line)
                continue
            label = match.group(1)
            if label.startswith("."):
                label = f"{current_global}{label}"
            else:
                current_global = label
            if label in lines:
                raise ValueError(f"{self.path.name} : label {label} défini deux fois")
            names.append(label)
            lines[label] = []
        result = {}
        for index, name in enumerate(names):
            body = tuple(lines[name])
            ends = bool(body) and body[-1].split()[0] in _TERMINATORS
            following = names[index + 1] if index + 1 < len(names) and not ends else None
            result[name] = _Block(body, following)
        return result

    def has_label(self, label: str) -> bool:
        return label in self.blocks

    def reachable_lines(self, label: str, checkver: bool | None) -> list[str]:
        """Lignes exécutables depuis `label`, dans l'ordre de découverte.

        `checkver` est la valeur de la commande checkver dans la version lue (vrai en Argent), ou None pour garder
        les deux branches."""
        return [line for block in self.reachable_blocks(label, checkver) for line in block]

    def reachable_blocks(self, label: str, checkver: bool | None) -> list[list[str]]:
        """Lignes exécutables depuis `label`, bloc par bloc dans l'ordre de découverte (cf. `reachable_lines`).

        Un bloc regroupe ce que fait une branche : choisir un lot, le donner, puis prendre les jetons."""
        if label not in self.blocks:
            raise ValueError(f"{self.path.name} : label {label} introuvable")
        result: list[list[str]] = []
        seen = {label}
        queue = deque([label])
        while queue:
            name = queue.popleft()
            lines, targets = self._run(name, checkver)
            result.append(lines)
            for target in targets:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return result

    @cached_property
    def constants(self) -> dict[str, int]:
        """Constantes numériques définies dans le fichier (« DEF GOLDENRODGAMECORNER_ABRA_COINS EQU 200 »)."""
        result = {}
        for line in source_lines(self.path):
            if match := _CONSTANT.match(line):
                result[match.group(1)] = parse_int(match.group(2))
        return result

    def _run(self, name: str, checkver: bool | None) -> tuple[list[str], list[str]]:
        """Lignes exécutées d'un bloc et blocs où l'exécution peut continuer."""
        block = self.blocks[name]
        lines: list[str] = []
        targets: list[str] = []
        after_checkver = False
        for line in block.lines:
            lines.append(line)
            command = line.split()[0]
            target = self._target(name, line, command)
            if after_checkver and checkver is not None and command in _BRANCHES:
                if command not in ("iftrue", "iffalse"):
                    raise ValueError(f"{self.path.name} : branche après checkver non prise en charge : {line}")
                if (command == "iftrue") == checkver:
                    return lines, [*targets, *([target] if target else [])]
            elif target:
                targets.append(target)
            after_checkver = command == _CHECKVER
        if block.following:
            targets.append(block.following)
        return lines, targets

    def _target(self, name: str, line: str, command: str) -> str | None:
        """Label du fichier vers lequel la ligne peut sauter (« .Local » est relatif au label global courant)."""
        if command not in _BRANCHES and command not in _JUMPS and command != _TRAINER:
            return None
        reference = macro_args(line, command)[-1]
        if reference.startswith("."):
            reference = f"{name.split('.')[0]}{reference}"
        return reference if reference in self.blocks else None
