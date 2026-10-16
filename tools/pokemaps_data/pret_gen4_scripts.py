"""Scripts de Platine écrits en assembleur (res/field/scripts, res/field/frontier_scripts), lus macro par macro.

Chaque ligne est une macro de asm/macros/scrcmd.inc et movement.inc (terrain) ou de frscrcmd.inc (Frontier),
dont le nombre d'arguments est vérifié contre sa définition, un label, une constante locale (#define) ou une
directive de données (.short, .byte, .long, .balign). Les macros composées (CallIfEq…) restent telles quelles :
leur sens est lu avec les conditions de scénario (phase 5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_source import read_text

FIELD_MACROS = ("asm/macros/scrcmd.inc", "asm/macros/movement.inc")
FRONTIER_MACROS = ("asm/macros/frscrcmd.inc",)
_MACRO = re.compile(r"^\s*\.macro\s+(\w+)(.*)$", re.MULTILINE)
_LABEL = re.compile(r"^(\w+):$")
_DEFINE = re.compile(r"^#define\s+(\w+)\s+(\S+)$")
_DIRECTIVES = frozenset({".short", ".byte", ".long", ".balign", ".data"})
_ENTRY_MACROS = frozenset({"ScriptEntry", "InitScriptEntry_OnFrameTable"})


@dataclass(frozen=True)
class MacroDefinition:
    name: str
    required: int
    total: int


@dataclass(frozen=True)
class MacroCall:
    line: int
    name: str
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class TextScriptFile:
    name: str
    entries: tuple[str, ...]  # labels des points d'entrée, dans l'ordre (numéros de script 1, 2…)
    defines: dict[str, str]
    # Lignes avant le premier label (table des entrées), puis contenu de chaque label dans l'ordre du fichier.
    header: tuple[MacroCall, ...]
    labels: dict[str, tuple[MacroCall, ...]]


def read_macros(root: Path, files: tuple[str, ...]) -> dict[str, MacroDefinition]:
    macros: dict[str, MacroDefinition] = {}
    for relative in files:
        for name, parameters in _MACRO.findall(read_text(root / relative)):
            # Paramètres séparés par des virgules ou des espaces. Comme pour l'assembleur GNU, un argument omis
            # est vide (ou prend sa valeur par défaut « nom = défaut ») ; seul « nom:req » est obligatoire.
            names = [p for p in re.split(r"[\s,]+", re.sub(r"\s*=\s*", "=", parameters.strip())) if p]
            required = sum(1 for p in names if p.endswith(":req"))
            if name in macros:
                raise ValueError(f"{root / relative} : macro {name} définie deux fois")
            macros[name] = MacroDefinition(name, required, len(names))
    return macros


def read_text_script(path: Path, macros: dict[str, MacroDefinition]) -> TextScriptFile:
    defines: dict[str, str] = {}
    header: list[MacroCall] = []
    labels: dict[str, list[MacroCall]] = {}
    current: list[MacroCall] = header
    for number, raw in enumerate(read_text(path).splitlines(), start=1):
        # Commentaires C et commentaires « @ » de l'assembleur ARM.
        line = re.sub(r"/\*.*?\*/|//.*$|@.*$", "", raw).strip()
        if not line or line.startswith(("#include", "# include")):
            continue
        if define := _DEFINE.match(line):
            defines[define.group(1)] = define.group(2)
        elif label := _LABEL.match(line):
            if label.group(1) in labels:
                raise ValueError(f"{path}:{number} : label répété : {label.group(1)}")
            current = labels.setdefault(label.group(1), [])
        else:
            current.append(_call(line, number, macros, path))
    entries = tuple(call.arguments[0] for call in header if call.name in _ENTRY_MACROS)
    if missing := [entry for entry in entries if entry not in labels]:
        raise ValueError(f"{path} : points d'entrée sans label : {missing}")
    return TextScriptFile(path.stem, entries, defines, tuple(header), {k: tuple(v) for k, v in labels.items()})


def _call(line: str, number: int, macros: dict[str, MacroDefinition], path: Path) -> MacroCall:
    name, _, rest = re.sub(r"\s+", " ", line).partition(" ")
    if "(" in rest and "," in rest[rest.index("(") :]:
        raise ValueError(f"{path}:{number} : virgule entre parenthèses non prise en charge")
    arguments = tuple(argument.strip() for argument in rest.split(",")) if rest.strip() else ()
    if name in _DIRECTIVES:
        return MacroCall(number, name, arguments)
    if name not in macros:
        raise ValueError(f"{path}:{number} : macro inconnue : {name}")
    definition = macros[name]
    if not definition.required <= len(arguments) <= definition.total:
        raise ValueError(f"{path}:{number} : {name} attend {definition.required} à {definition.total} arguments")
    return MacroCall(number, name, arguments)


def read_platinum_scripts(root: Path, scripts_order: dict[str, int]) -> dict[int, TextScriptFile]:
    """Scripts du terrain, numérotés selon scripts.order (numéros des en-têtes de lieux)."""
    macros = read_macros(root, FIELD_MACROS)
    return {
        index: read_text_script(root / f"res/field/scripts/{name}.s", macros) for name, index in scripts_order.items()
    }


def read_frontier_scripts(root: Path) -> dict[str, TextScriptFile]:
    macros = read_macros(root, FRONTIER_MACROS)
    folder = root / "res/field/frontier_scripts"
    return {path.stem: read_text_script(path, macros) for path in sorted(folder.glob("*.s"))}
