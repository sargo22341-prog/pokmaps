"""Points de départ des offres d'un lieu DS : événements du lieu et scripts lancés à l'entrée dans le lieu.

Un PNJ, une case qu'on examine ou un déclencheur au sol lance le script que désigne son numéro ; les tables
d'initialisation du lieu lancent aussi des scripts à l'arrivée (type fixe) ou dès qu'une variable prend une valeur
(table des conditions, vérifiée à chaque image). Chaque numéro est ramené à un fichier et un point d'entrée
(pret_gen4_script_ranges). Les tranches déjà lues ailleurs sont écartées : dresseurs (pret_gen4_battles), objets au
sol et cachés (pret_gen4_field_items) ; les arbres à baies, dont la baie est celle que le joueur plante ou celle
que pose le moteur au départ, relèvent du sol meuble (phase 8). 0xFFFF ne désigne aucun script : le moteur ne
lance rien pour un tel PNJ.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_field_items import HIDDEN_ITEM_EVENT
from .pret_gen4_flow import is_var
from .pret_gen4_flow_chains import Condition
from .pret_gen4_script_binary import InitScripts
from .pret_gen4_scripts import TextScriptFile
from .pret_gen4_source import c_defines

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header

NO_SCRIPT = 0xFFFF
_BERRY_TREES = 2800  # SCRIPT_ID_OFFSET_BERRY_TREE_INTERACTIONS ; même début dans Diamant/Perle
# Macros des tables d'initialisation de Platine -> type (include/constants/init_script_types.h).
_PLATINUM_FIXED = {
    "InitScriptEntry_OnTransition": "INIT_SCRIPT_ON_TRANSITION",
    "InitScriptEntry_OnResume": "INIT_SCRIPT_ON_RESUME",
    "InitScriptEntry_OnLoad": "INIT_SCRIPT_ON_LOAD",
}
_PLATINUM_ENDS = frozenset({"InitScriptEntryEnd", "InitScriptEnd", "InitScriptFrameTableEnd"})


@dataclass(frozen=True)
class OfferSite:
    header: str
    kind: str  # object (PNJ), background (case examinée), trigger (déclencheur au sol), scene (initialisation)
    event: int  # rang de l'événement dans sa liste ; pour une scène, rang dans la table d'initialisation
    x: int | None
    z: int | None
    script_file: int
    entry: int  # rang du point d'entrée dans le fichier de scripts
    conditions: tuple[Condition, ...]  # variable d'un déclencheur ou d'une ligne de table des conditions


def offer_sites(repo: Gen4PretRepo, header: Gen4Header) -> tuple[tuple[OfferSite, ...], tuple[str, ...]]:
    """Points de départ du lieu, puis les événements dont le numéro dépasse la table des scripts du fichier : le
    moteur lirait alors au-delà de la table, ce qu'aucun joueur ne déclenche normalement (panneau inutilisé)."""
    events = repo.events[header.events]
    ids = repo.script_ids
    excluded = ((ids.single, ids.hidden_end), (_BERRY_TREES, ids.single))
    rows: list[tuple[str, int, int, int | None, int | None, tuple[Condition, ...]]] = []
    rows += [("object", rank, obj.script, obj.x, obj.z, ()) for rank, obj in enumerate(events.object_events)]
    rows += [
        ("background", rank, event.script, event.x, event.z, ())
        for rank, event in enumerate(events.bg_events)
        if event.kind != HIDDEN_ITEM_EVENT
    ]
    rows += [
        ("trigger", rank, event.script, event.x, event.z, (Condition(f"var:{event.var}", "=", event.value),))
        for rank, event in enumerate(events.coord_events)
    ]
    rows += [
        ("scene", rank, script, None, None, conditions)
        for rank, (script, conditions) in enumerate(_scenes(repo, header))
    ]
    result = []
    outside = []
    for kind, rank, script, x, z, conditions in rows:
        if script in {0, NO_SCRIPT} or any(low <= script < high for low, high in excluded):
            continue
        found = _locate(repo, header, script)
        if found is None:
            outside.append(f"{header.constant} {kind} {rank} : script {script}")
            continue
        file, entry = found
        result.append(OfferSite(header.constant, kind, rank, x, z, file, entry, conditions))
    return tuple(result), tuple(outside)


def _locate(repo: Gen4PretRepo, header: Gen4Header, script: int) -> tuple[int, int] | None:
    found = repo.script_ranges.locate(script)
    file, entry = found if found is not None else (header.scripts, script - 1)
    if file not in repo.flows or not 0 <= entry < len(repo.flows[file].entries):
        return None
    return file, entry


def _scenes(repo: Gen4PretRepo, header: Gen4Header) -> list[tuple[int, tuple[Condition, ...]]]:
    """Scripts des tables d'initialisation : (numéro, condition de la table des conditions)."""
    table = repo.init_scripts[header.init_scripts] if not repo.platinum else _platinum_init(repo, header)
    scenes: list[tuple[int, tuple[Condition, ...]]] = [(script, ()) for _, script in table.fixed]
    for var, value, script in table.frame_table:
        # La ligne compare deux valeurs lues comme des variables : une constante sous 0x4000 reste elle-même.
        scenes.append((script, (Condition(f"var:{var}", "=", f"var:{value}" if is_var(value) else value),)))
    return scenes


def _platinum_init(repo: Gen4PretRepo, header: Gen4Header) -> InitScripts:
    """Table d'initialisation de Platine, lue dans son fichier .s (macros InitScriptEntry_… et InitScriptGoTo…)."""
    script = repo.scripts[header.init_scripts]
    if not isinstance(script, TextScriptFile):
        raise ValueError(f"{header.constant} : initialisation de Platine illisible")
    types = c_defines(repo.root / "include/constants/init_script_types.h", "INIT_SCRIPT_ON_")
    fixed = []
    frame: list[tuple[int, int, int]] = []
    for call in script.header:
        if call.name == "InitScriptEnd":
            break  # données de remplissage éventuelles après la fin de la table
        if call.name in _PLATINUM_FIXED:
            fixed.append((types[_PLATINUM_FIXED[call.name]], _number(call.arguments[0], repo, header)))
        elif call.name == "InitScriptEntry_Fixed":
            fixed.append((_number(call.arguments[0], repo, header), _number(call.arguments[1], repo, header)))
        elif call.name == "InitScriptEntry_OnFrameTable":
            for row in script.labels[call.arguments[0]]:
                if row.name in _PLATINUM_ENDS:
                    break
                if row.name != "InitScriptGoToIfEqual":
                    raise ValueError(f"{header.constant} : ligne de table des conditions inconnue : {row.name}")
                var, value, number = (_number(argument, repo, header) for argument in row.arguments)
                frame.append((var, value, number))
        elif call.name not in _PLATINUM_ENDS:
            raise ValueError(f"{header.constant} : entrée d'initialisation inconnue : {call.name}")
    return InitScripts(tuple(fixed), tuple(frame))


def _number(text: str, repo: Gen4PretRepo, header: Gen4Header) -> int:
    if text in repo.constants:
        return repo.constants[text]
    try:
        return int(text, 0)
    except ValueError as error:
        raise ValueError(f"{header.constant} : valeur d'initialisation illisible : {text}") from error
