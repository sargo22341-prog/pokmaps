"""Parsing des en-tetes, blocs et evenements de cartes des depots pret."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret import FIRST_INDOOR_MAP
from .pret_source import macro_args, parse_int, source_lines
from .pret_models import Connection, MapObject, PretMap, Warp

if TYPE_CHECKING:
    from .pret import PretRepo



def maps(repo: PretRepo) -> dict[str, PretMap]:
    """Toutes les cartes qui ont un en-tête, indexées par constante."""
    blocks = block_files(repo)
    objects = read_objects(repo)
    hidden = hidden_items(repo)
    result = {}
    for header in sorted(repo.path("data/maps/headers").glob("*.asm")):
        lines = source_lines(header)
        label, const, tileset = macro_args(lines[0], "map_header")[:3]
        number, width, height = repo.map_constants[const]
        border, warps, signs, objs = objects[label]
        data = repo.path(blocks[label]).read_bytes()
        if len(data) > width * height:
            raise ValueError(f"{header.name} : {len(data)} blocs pour {width} × {height}")
        # Quelques fichiers sont plus courts que la carte (le jeu lit alors les octets suivants de la ROM,
        # hors de la zone accessible) : on complète avec le bloc de bordure.
        data += bytes([border]) * (width * height - len(data))
        outdoor = number < repo.map_constants[FIRST_INDOOR_MAP][0]
        pret_map = PretMap(
            const, number, label, width, height, tileset, data, border, outdoor, [], warps, signs, objs
        )
        for line in lines[1:]:
            if line.startswith("connection "):
                direction, _, target, offset = macro_args(line, "connection")
                pret_map.connections.append(Connection(direction, target, parse_int(offset)))
        pret_map.objects += [MapObject(x, y, "hidden_item", item=item) for x, y, item in hidden.get(const, [])]
        result[const] = pret_map
    return result


def block_files(repo: PretRepo) -> dict[str, str]:
    """Label de carte -> fichier .blk (plusieurs cartes peuvent partager le même fichier)."""
    files = {}
    pending: list[str] = []
    label_re = re.compile(r"^(\w+)_Blocks:")
    incbin_re = re.compile(r'INCBIN\s+"([^"]+\.blk)"')
    for line in source_lines(repo.path("maps.asm")):
        label = label_re.match(line)
        if label:
            pending.append(label.group(1))
        incbin = incbin_re.search(line)
        if incbin:
            for name in pending:
                files[name] = incbin.group(1)
            pending = []
    return files


def read_objects(repo: PretRepo) -> dict[str, tuple[int, list[Warp], list[tuple[int, int]], list[MapObject]]]:
    result = {}
    for path in sorted(repo.path("data/maps/objects").glob("*.asm")):
        label = None
        border = 0
        warps: list[Warp] = []
        signs: list[tuple[int, int]] = []
        objs: list[MapObject] = []
        for line in source_lines(path):
            if line.endswith("_Object:"):
                label = line[: -len("_Object:")]
            elif line.startswith("db $") and label and not warps and not objs:
                border = parse_int(line[3:])
            elif line.startswith("warp_event "):
                x, y, target, target_warp = macro_args(line, "warp_event")
                warps.append(Warp(int(x), int(y), target, int(target_warp)))
            elif line.startswith("bg_event "):
                x, y, _ = macro_args(line, "bg_event")
                signs.append((int(x), int(y)))
            elif line.startswith("object_event "):
                objs.append(_object_event(macro_args(line, "object_event")))
            elif line.startswith("def_warps_to"):
                break
        if label is None:
            raise ValueError(f"{path.name} : label _Object introuvable")
        result[label] = (border, warps, signs, objs)
    return result


def hidden_items(repo: PretRepo) -> dict[str, list[tuple[int, int, str]]]:
    """Objets cachés (Cherch'Objet) : constante de carte -> [(x, y, objet)]."""
    result: dict[str, list[tuple[int, int, str]]] = {}
    current = None
    for line in source_lines(repo.path("data/events/hidden_events.asm")):
        if line.startswith("hidden_events_for "):
            current = line.split()[1]
        elif line.startswith("hidden_event ") and current:
            x, y, function, argument = macro_args(line, "hidden_event")
            if function == "HiddenItems":
                result.setdefault(current, []).append((int(x), int(y), argument))
    return result



def _object_event(args: list[str]) -> MapObject:
    x, y, sprite = int(args[0]), int(args[1]), args[2]
    text = args[5] if len(args) > 5 else None
    if len(args) == 8:
        if args[6].startswith("OPP_"):
            return MapObject(x, y, "trainer", sprite, trainer_class=args[6], trainer_number=int(args[7]), text=text)
        return MapObject(x, y, "pokemon", sprite, pokemon=args[6], level=int(args[7]), text=text)
    if len(args) == 7 and args[6] != "0":
        return MapObject(x, y, "item", sprite, item=args[6], text=text)
    return MapObject(x, y, "npc", sprite, text=text)
