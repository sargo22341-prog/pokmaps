"""Plans éditoriaux des zones d'un même niveau, sans les maisons accessibles par leurs portes."""

from __future__ import annotations

import csv
from dataclasses import dataclass

from .games import map_families
from .pret import BLOCK_PX, STEP_PX
from .pret_models import PretMap
from .sources import DATA_DIR


@dataclass(frozen=True)
class PlanPart:
    family: str
    plan: str
    number: int
    name: str
    map: str
    x: int
    y: int


@dataclass(frozen=True)
class MapPlan:
    const: str
    number: int
    name: str
    parts: tuple[PlanPart, ...]
    width: int
    height: int


def read_plans() -> tuple[PlanPart, ...]:
    with (DATA_DIR / "map_plans.csv").open(encoding="utf-8", newline="") as handle:
        parts = tuple(
            PlanPart(
                row["family"],
                row["plan"],
                int(row["number"]),
                row["name_fr"],
                row["map"],
                int(row["x"]) * STEP_PX,
                int(row["y"]) * STEP_PX,
            )
            for row in csv.DictReader(handle)
        )
    seen: set[tuple[str, str]] = set()
    numbers: dict[tuple[str, int], str] = {}
    for part in parts:
        key = (part.family, part.map)
        number = (part.family, part.number)
        if key in seen or part.family not in map_families() or not part.name.strip() or not 900 <= part.number < 998:
            raise ValueError(f"map_plans.csv : zone ou numéro invalide : {part}")
        if part.x < 0 or part.y < 0 or numbers.get(number, part.plan) != part.plan:
            raise ValueError(f"map_plans.csv : placement ou numéro partagé : {part}")
        seen.add(key)
        numbers[number] = part.plan
    return parts


def build_plans(parts: tuple[PlanPart, ...], maps: dict[str, PretMap], detached: set[str]) -> dict[str, MapPlan]:
    groups: dict[str, list[PlanPart]] = {}
    for part in parts:
        if part.map not in maps:
            continue  # Certaines salles n'existent que dans Cristal.
        if part.map not in detached:
            raise ValueError(f"map_plans.csv : zone non accessible ou sur la carte du monde : {part.map}")
        groups.setdefault(part.plan, []).append(part)
    result = {}
    for const, members in groups.items():
        if const in maps or len({(part.number, part.name) for part in members}) != 1:
            raise ValueError(f"map_plans.csv : définition contradictoire de {const}")
        _check_overlap(const, members, maps)
        width = max(part.x + maps[part.map].width * BLOCK_PX for part in members)
        height = max(part.y + maps[part.map].height * BLOCK_PX for part in members)
        if max(width, height) > 8192:
            raise ValueError(f"map_plans.csv : plan trop grand : {const}")
        result[const] = MapPlan(const, members[0].number, members[0].name, tuple(members), width, height)
    return result


def _check_overlap(const: str, parts: list[PlanPart], maps: dict[str, PretMap]) -> None:
    for index, part in enumerate(parts):
        current = maps[part.map]
        for other in parts[:index]:
            previous = maps[other.map]
            horizontal = part.x < other.x + previous.width * BLOCK_PX and other.x < part.x + current.width * BLOCK_PX
            vertical = part.y < other.y + previous.height * BLOCK_PX and other.y < part.y + current.height * BLOCK_PX
            if horizontal and vertical:
                raise ValueError(f"map_plans.csv : {part.map} recouvre {other.map} dans {const}")
