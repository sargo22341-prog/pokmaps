"""Passages GBA sans warp : plongées scriptées, téléphérique et entrées des Bases Secrètes.

- Plongée : le script d'une carte fixe la destination de Plongée (`setdivewarp`). Le passage est placé à
  l'arrivée de la liaison inverse, sinon sur la case de plongée la plus centrale de la carte. Une destination
  qui dépend de la case du joueur (`getplayerxy`) est placée sur cette case : remonter au Sanctuaire n'est
  possible qu'au-dessus de son entrée.
- Téléphérique : `CableCarWarp` (src/field_specials.c) amène à la même case de chacune des deux stations.
- Base Secrète : chaque événement `secret_base` mène au warp d'entrée de la carte modèle de son groupe,
  donnée par la table des entrées de src/secret_base.c.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .maps import WarpRow
from .maps_terrain_gen3 import behavior_constants
from .pret_gen3_scripts import Instruction, ScriptBlock, parse_scripts
from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .maps_layout_gen3 import Gen3GameMaps
    from .pret_gen3_maps import Gen3Map

_ON_DIVE = re.compile(r"^\s*map_script\s+MAP_SCRIPT_ON_DIVE_WARP\s*,\s*(\w+)\s*$", re.M)
_CABLE_CAR = re.compile(r"SetWarpDestination\(MAP_GROUP\((MAP_\w+)\),\s*MAP_NUM\(\1\),\s*[^,]+,\s*(\d+),\s*(\d+)\)")
_BASE_ENTRANCE = re.compile(r"MAP_NUM\((MAP_SECRET_BASE_\w+)\),\s*(\d+),\s*\d+,\s*\d+\b")


@dataclass(frozen=True)
class DiveLink:
    source: str
    target: str
    x: int  # case d'arrivée dans `target`
    y: int
    condition: tuple[int, int] | None  # case de `source` exigée par le script, None si toutes conviennent


def passages(game_maps: Gen3GameMaps) -> list[WarpRow]:
    if game_maps.repo.remake:
        return []
    return dive_passages(game_maps) + cable_car_passages(game_maps) + secret_base_passages(game_maps)


def dive_links(game_maps: Gen3GameMaps) -> list[DiveLink]:
    links = []
    for const, current in sorted(game_maps.maps.items()):
        relative = f"data/maps/{current.shared_scripts_map or current.label}/scripts.inc"
        if const not in game_maps.placements or not (game_maps.repo.root / relative).is_file():
            continue
        text = read_text(game_maps.repo.root / relative)
        if "setdivewarp" not in text:
            continue
        blocks = parse_scripts(text, relative)
        conditions = _dive_conditions(blocks, _ON_DIVE.search(text))
        for label, block in blocks.items():
            for instruction in block.lines:
                if instruction.command == "setdivewarp":
                    target, x, y = _dive_target(instruction)
                    links.append(DiveLink(const, target, x, y, conditions.get(label)))
    return links


def _dive_target(instruction: Instruction) -> tuple[str, int, int]:
    args = instruction.args
    # Rubis et Saphir gardent le numéro de warp 255 avant les coordonnées.
    if len(args) == 4 and args[1] == "255":
        args = (args[0], args[2], args[3])
    if len(args) != 3:
        raise ValueError(f"{instruction.source} : setdivewarp inattendu : {instruction.args}")
    return args[0], int(args[1]), int(args[2])


def _dive_conditions(blocks: dict[str, ScriptBlock], match: re.Match[str] | None) -> dict[str, tuple[int, int]]:
    """Label exécuté seulement sur une case précise -> cette case (`getplayerxy` puis comparaisons)."""
    if match is None:
        return {}
    lines = blocks[match[1]].lines
    if not lines or lines[0].command != "getplayerxy":
        raise ValueError(f"{match[1]} : script de Plongée sans position du joueur")
    wanted: dict[str, int] = {}
    pending: tuple[str, int] | None = None
    for instruction in lines[1:]:
        args = instruction.args
        if instruction.command == "compare":
            pending = (args[0], int(args[1]))
        elif instruction.command == "goto_if_ne" and len(args) == 3:
            wanted[args[0]] = int(args[1])
        elif instruction.command == "goto_if_ne" and pending is not None:
            wanted[pending[0]] = pending[1]
            pending = None
        elif instruction.command == "goto" and set(wanted) == {"VAR_0x8004", "VAR_0x8005"}:
            return {args[0]: (wanted["VAR_0x8004"], wanted["VAR_0x8005"])}
        else:
            raise ValueError(f"{instruction.source} : condition de Plongée inattendue : {instruction.command}")
    raise ValueError(f"{match[1]} : case de Plongée introuvable")


def dive_passages(game_maps: Gen3GameMaps) -> list[WarpRow]:
    links = dive_links(game_maps)
    rows = []
    for link in links:
        if link.target not in game_maps.placements:
            raise ValueError(f"{link.source} : destination de Plongée absente : {link.target}")
        conditional = {other.condition for other in links if other.source == link.source and other.condition}
        if link.condition is not None:
            start = link.condition
        else:
            arrivals = sorted({(other.x, other.y) for other in links if other.target == link.source})
            # Remonter ailleurs que sur la case réservée d'une autre destination : aucune case précise ne convient.
            if arrivals and set(arrivals) <= conditional:
                continue
            start = arrivals[0] if arrivals else _central_dive_cell(game_maps, game_maps.maps[link.source])
            if start is None:
                continue  # Destination déclarée sans aucune case où plonger (couloir du sous-sol de l'Épave).
        source = game_maps.point(link.source, *start)
        rows.append(WarpRow(link.source, *source, link.target, *game_maps.point(link.target, link.x, link.y), "dive"))
    return rows


def _central_dive_cell(game_maps: Gen3GameMaps, current: Gen3Map) -> tuple[int, int] | None:
    """Case de plongée la plus proche du centre de celles de la carte, None si la carte n'en a aucune."""
    diving = _dive_behaviors(game_maps)
    repo = game_maps.repo
    primary = repo.tilesets[current.layout.primary_tileset]
    secondary = repo.tilesets[current.layout.secondary_tileset]
    cells = []
    for y in range(current.height):
        for x in range(current.width):
            number = current.block(x, y)
            source = primary if number < primary.primary_metatile_count else secondary
            index = number if source is primary else number - primary.primary_metatile_count
            if source.metatiles[index].behavior in diving:
                cells.append((x, y))
    if not cells:
        return None
    cx = sum(x for x, _ in cells) / len(cells)
    cy = sum(y for _, y in cells) / len(cells)
    return min(cells, key=lambda cell: ((cell[0] - cx) ** 2 + (cell[1] - cy) ** 2, cell))


def _dive_behaviors(game_maps: Gen3GameMaps) -> frozenset[int]:
    """Comportements où le moteur autorise la Plongée (`MetatileBehavior_IsDiveable`)."""
    text = read_text(game_maps.repo.root / "src/metatile_behavior.c")
    body = re.search(r"bool8 MetatileBehavior_IsDiveable\(u8 metatileBehavior\)\s*\{(.*?)\n\}", text, re.S)
    constants = behavior_constants(game_maps.repo)
    names = re.findall(r"\b(MB_\w+)\b", body[1]) if body else []
    if not names or any(name not in constants for name in names):
        raise ValueError(f"{game_maps.repo.root} : comportements de Plongée introuvables")
    return frozenset(constants[name] for name in names)


def cable_car_passages(game_maps: Gen3GameMaps) -> list[WarpRow]:
    text = read_text(game_maps.repo.root / "src/field_specials.c")
    body = re.search(r"void CableCarWarp\(void\)\s*\{(.*?)\n\}", text, re.S)
    stations = _CABLE_CAR.findall(body[1]) if body else []
    if len(stations) != 2 or any(const not in game_maps.placements for const, _, _ in stations):
        raise ValueError(f"{game_maps.repo.root} : deux stations de téléphérique attendues : {stations}")
    (first, x1, y1), (second, x2, y2) = stations
    one, other = game_maps.point(first, int(x1), int(y1)), game_maps.point(second, int(x2), int(y2))
    return [WarpRow(first, *one, second, *other, "cable_car"), WarpRow(second, *other, first, *one, "cable_car")]


def secret_base_passages(game_maps: Gen3GameMaps) -> list[WarpRow]:
    entrances = {
        const: int(warp) for const, warp in _BASE_ENTRANCE.findall(read_text(game_maps.repo.root / "src/secret_base.c"))
    }
    rows = []
    for const in sorted(game_maps.placements):
        for event in game_maps.maps[const].bg_events:
            if event.kind != "secret_base":
                continue
            base = re.fullmatch(r"SECRET_BASE_(\w+?)_\d+", str(event.value("secret_base_id")))
            target = f"MAP_SECRET_BASE_{base[1]}" if base else ""
            if target not in entrances or target not in game_maps.placements:
                raise ValueError(f"{const} : Base Secrète inconnue : {event.value('secret_base_id')}")
            arrival = game_maps.maps[target].warps[entrances[target]]
            source = game_maps.point(const, event.x, event.y)
            rows.append(WarpRow(const, *source, target, *game_maps.point(target, arrival.x, arrival.y), "secret_base"))
    return rows
