"""Objets au sol et objets cachés des lieux DS, avec le drapeau qui les retire une fois ramassés.

Un objet au sol est un PNJ (Poké Ball, posé par les événements du lieu ou, au Monde Distorsion de Platine, par le
moteur : pret_gen4_distortion) dont le script appartient à la tranche des objets au sol : son point
d'entrée dans le fichier commun fixe l'objet et la quantité (VAR_0x8008 et VAR_0x8009 en Platine, mêmes variables
dans Diamant/Perle) avant de les donner ; son drapeau de masquage est celui qui le retire. Un objet caché est un
événement de fond (type BG_EVENT_TYPE_HIDDEN_ITEM) : le moteur cherche l'objet et la quantité dans gHiddenItems
(Platine, include/data/field/hidden_items.h) ou UNK_020F2DB4 (Diamant/Perle, 229 entrées de 8 octets), d'après
le numéro du script, et en déduit le drapeau (Script_GetHiddenItemFlag, sub_02039694). Diamant/Perle compare
seulement l'octet bas de ce numéro (lsl #0x18 avant la recherche).

Le Casino de Voilaroc n'a pas de jetons cachés dans ces jeux : les objets cachés ne donnent que des objets, et
aucun événement de fond d'un lieu ne mène à une commande qui donne des jetons. `hidden_coin_events` le vérifie.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen4_distortion import read_distortion_objects
from .pret_gen4_engine_text import asm_data, asm_function, c_initializer
from .pret_gen4_flow import ADD_COINS, ADD_ITEM, Step, is_var, reachable
from .pret_gen4_flow_values import values_at
from .pret_gen4_map_models import BgEvent
from .pret_gen4_source import c_defines, metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo
    from .pret_gen4_map_models import Gen4Header
    from .pret_gen4_script_ids import ScriptIds

HIDDEN_ITEM_EVENT = 2
_MAX_QUANTITY = 999
_DP_TABLE_FILE = "arm9/asm/unk_02038C78.s"
_DP_TABLE = "UNK_020F2DB4"
_DP_ROWS = 0xE5
_DP_LOOKUP = (
    "ldr r2, _02039750",
    "lsl r0, r0, #0x18",
    "ldrh r0, [r2, #0x6]",
    "add r2, #0x8",
    f"cmp r1, #{_DP_ROWS:#x}",
)
_DP_READ = ("ldrh r1, [r1, r0]", "ldrb r0, [r0, #0x2]")


@dataclass(frozen=True)
class Gen4MapItem:
    header: int
    kind: str  # item (au sol) ou hidden_item
    x: int
    z: int
    y: int
    item: str
    quantity: int
    flag: int  # drapeau qui retire l'objet une fois ramassé
    script: int


@dataclass(frozen=True)
class _HiddenEntry:
    item: int
    quantity: int
    script: int


def item_names(repo: Gen4PretRepo) -> dict[int, str]:
    """Constante de chaque numéro d'objet du dépôt."""
    if repo.platinum:
        values = metang_enum(repo.root / "generated/items.txt")
    else:
        values = c_defines(repo.root / "include/constants/items.h", "ITEM_")
    names = {value: name for name, value in values.items()}
    if len(names) != len(values) or names.get(0) != "ITEM_NONE":
        raise ValueError(f"{repo.root} : numéros d'objets répétés ou ITEM_NONE absent")
    return names


def read_map_items(repo: Gen4PretRepo, ids: ScriptIds, selected: dict[int, Gen4Header]) -> tuple[Gen4MapItem, ...]:
    """Objets au sol et cachés des lieux `selected`."""
    names = item_names(repo)
    headers = [selected[index] for index in sorted(selected)]
    balls = _placed_balls(repo, ids, headers)
    visible = _visible_contents(repo, ids, {ball.script - ids.visible for ball in balls})
    hidden = _hidden_table(repo)
    result = []
    for ball in balls:
        item, quantity = visible[ball.script - ids.visible]
        if not ball.hidden_flag:
            raise ValueError(f"{ball.header.constant} : objet au sol sans drapeau ({ball.script})")
        values = (ball.x, ball.z, ball.y, names[item], quantity, ball.hidden_flag, ball.script)
        result.append(Gen4MapItem(ball.header.index, "item", *values))
    for header in headers:
        for event in repo.events[header.events].bg_events:
            if event.kind == HIDDEN_ITEM_EVENT:
                result.append(_hidden(header.index, header.constant, event, hidden, ids, names, repo.platinum))
    return tuple(result)


@dataclass(frozen=True)
class _Placed:
    header: Gen4Header
    x: int
    z: int
    y: int
    hidden_flag: int
    script: int


def _placed_balls(repo: Gen4PretRepo, ids: ScriptIds, headers: list[Gen4Header]) -> list[_Placed]:
    """Objets au sol posés dans les lieux, y compris par le moteur du Monde Distorsion (pret_gen4_distortion)."""
    result = [
        _Placed(header, obj.x, obj.z, obj.y, obj.hidden_flag, obj.script)
        for header in headers
        for obj in repo.events[header.events].object_events
        if ids.visible <= obj.script < ids.hidden
    ]
    if not repo.platinum:
        return result
    by_constant = {header.constant: header for header in headers}
    for obj in read_distortion_objects(repo):
        if obj.header not in by_constant or obj.script is None or not ids.visible <= obj.script < ids.hidden:
            continue
        if obj.x is None or obj.z is None or obj.y is None:
            raise ValueError(f"{obj.name} : position illisible")
        result.append(_Placed(by_constant[obj.header], obj.x, obj.z, obj.y, obj.hidden_flag or 0, obj.script))
    return result


def _visible_contents(repo: Gen4PretRepo, ids: ScriptIds, scripts: set[int]) -> dict[int, tuple[int, int]]:
    """Objet et quantité donnés par chaque point d'entrée employé du fichier des objets au sol."""
    flow = repo.flows[ids.visible_file]
    gives = [step for step in flow.steps.values() if step.command == ADD_ITEM]
    if len(gives) != 1 or not all(is_var(arg) for arg in gives[0].arguments[:2]):
        raise ValueError(f"{flow.name} : don d'objet attendu une seule fois, par variables")
    item_var, quantity_var = (int(arg) for arg in gives[0].arguments[:2])
    contents = {}
    for index in sorted(scripts):
        if index >= len(flow.entries):
            raise ValueError(f"{flow.name} : point d'entrée d'objet au sol absent : {index}")
        entry = (flow.entries[index],)
        found = values_at(flow, _gives_item, {item_var, quantity_var}, entry, repo.common_scripts)
        item, quantity = found.values(gives[0].key, item_var), found.values(gives[0].key, quantity_var)
        if len(item) != 1 or len(quantity) != 1:
            raise ValueError(f"{flow.name} : objet du point d'entrée {index} illisible : {item}, {quantity}")
        contents[index] = _checked(next(iter(item)), next(iter(quantity)), f"{flow.name} entrée {index}")
    return contents


def _gives_item(step: Step) -> bool:
    return step.command == ADD_ITEM


def _checked(item: object, quantity: object, where: str) -> tuple[int, int]:
    if not isinstance(item, int) or not isinstance(quantity, int) or not 1 <= quantity <= _MAX_QUANTITY or not item:
        raise ValueError(f"{where} : objet ou quantité invalide : {item}, {quantity}")
    return item, quantity


def _hidden_table(repo: Gen4PretRepo) -> tuple[_HiddenEntry, ...]:
    if repo.platinum:
        flags = metang_enum(repo.root / "generated/vars_flags.txt")
        items = metang_enum(repo.root / "generated/items.txt")
        body = c_initializer(
            read_text(repo.root / "include/data/field/hidden_items.h"), "gHiddenItems", "hidden_items.h"
        )
        rows = re.findall(r"HIDDEN_ITEM_ENTRY\((\w+),\s*(\d+),\s*(\d+),\s*(\w+)\)", body)
        if len(rows) != body.count("HIDDEN_ITEM_ENTRY") or not rows:
            raise ValueError(f"{repo.root} : gHiddenItems illisible")
        start = flags["HIDDEN_ITEM_FLAGS_START"]
        return tuple(_HiddenEntry(items[item], int(qty), flags[flag] - start) for item, qty, _range, flag in rows)
    text = read_text(repo.root / _DP_TABLE_FILE)
    body = asm_function(text, "sub_020396E8", _DP_TABLE_FILE)
    if any(line not in body for line in (*_DP_LOOKUP, *_DP_READ)):
        raise ValueError(f"{repo.root / _DP_TABLE_FILE} : recherche des objets cachés modifiée")
    data = asm_data(text, _DP_TABLE, _DP_TABLE_FILE)
    if len(data) != 8 * _DP_ROWS:
        raise ValueError(f"{repo.root / _DP_TABLE_FILE} : {len(data)} octets pour les objets cachés")
    return tuple(
        _HiddenEntry(
            int.from_bytes(data[at : at + 2], "little"), data[at + 2], int.from_bytes(data[at + 6 : at + 8], "little")
        )
        for at in range(0, len(data), 8)
    )


def _hidden(
    header: int,
    constant: str,
    event: BgEvent,
    table: tuple[_HiddenEntry, ...],
    ids: ScriptIds,
    names: dict[int, str],
    platinum: bool,
) -> Gen4MapItem:
    script = event.script
    if not ids.hidden <= script < ids.hidden_end:
        raise ValueError(f"{constant} : objet caché hors de la tranche des objets cachés : {script}")
    wanted = script - ids.hidden
    # Diamant/Perle ne compare que l'octet bas du numéro (sub_020396E8).
    key = wanted if platinum else wanted & 0xFF
    entry = next((row for row in table if row.script == key), None)
    if entry is None or entry.item not in names:
        raise ValueError(f"{constant} : objet caché {script} absent de la table du moteur")
    item, quantity = _checked(entry.item, entry.quantity, f"{constant} objet caché {script}")
    flag = wanted + ids.hidden_flag_base
    return Gen4MapItem(header, "hidden_item", event.x, event.z, event.y, names[item], quantity, flag, script)


def hidden_coin_events(repo: Gen4PretRepo) -> list[tuple[str, int]]:
    """Événements de fond qui mènent à un don de jetons (lieu, numéro d'événement) : aucun attendu."""
    found = []
    for header in repo.headers.values():
        flow = repo.flows.get(header.scripts)
        if flow is None:
            continue
        for index, event in enumerate(repo.events[header.events].bg_events):
            if event.kind == HIDDEN_ITEM_EVENT or not 1 <= event.script <= len(flow.entries):
                continue
            steps = reachable(flow, flow.entries[event.script - 1])
            if any(flow.steps[key].command == ADD_COINS for key in steps):
                found.append((header.constant, index))
    return found
