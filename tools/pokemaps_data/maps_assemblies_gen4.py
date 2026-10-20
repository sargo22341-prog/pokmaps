"""Plans DS de même étage : assemblage des tuiles natives et translation de leurs contenus."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from .maps import GameMapData, MapRow
from .maps_layout import identifier
from .maps_render import TILE_SIZE, level_count
from .maps_tiles_gen4 import write_pyramid
from .sources import DATA_DIR


@dataclass(frozen=True)
class AssemblyPart:
    plan: str
    number: int
    name: str
    source: str
    x: int
    y: int


def read_assemblies(family: str) -> tuple[AssemblyPart, ...]:
    with (DATA_DIR / "map_assemblies_gen4.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["family", "plan", "number", "name_fr", "map", "x", "y"]:
            raise ValueError("map_assemblies_gen4.csv : colonnes invalides")
        all_rows = list(reader)
    if len(all_rows) > 512 or any(row["family"] not in {"platinum", "diamond-pearl"} for row in all_rows):
        raise ValueError("map_assemblies_gen4.csv : famille inconnue ou trop de parties")
    rows = [row for row in all_rows if row["family"] == family]
    result = tuple(
        AssemblyPart(row["plan"], int(row["number"]), row["name_fr"], row["map"], int(row["x"]), int(row["y"]))
        for row in rows
    )
    seen = set()
    definitions = {}
    numbers = {}
    for part in result:
        if part.source in seen or not 700 <= part.number < 900 or not part.name:
            raise ValueError(f"map_assemblies_gen4.csv : définition répétée ou invalide : {part}")
        if min(part.x, part.y) < 0 or part.x % TILE_SIZE or part.y % TILE_SIZE:
            raise ValueError(f"map_assemblies_gen4.csv : placement hors grille de tuiles : {part}")
        definition = (part.number, part.name)
        if definitions.get(part.plan, definition) != definition or numbers.get(part.number, part.plan) != part.plan:
            raise ValueError(f"map_assemblies_gen4.csv : étage contradictoire : {part.plan}")
        seen.add(part.source)
        definitions[part.plan] = definition
        numbers[part.number] = part.plan
    return result


def assemble_floors(data: GameMapData, output: Path, family: str) -> None:
    parts = read_assemblies(family)
    maps = {row.const: row for row in data.maps}
    native = {row.const: row.parent or row.const for row in data.maps}
    groups: dict[str, list[AssemblyPart]] = {}
    for part in parts:
        if part.source not in maps or maps[part.source].parent:
            raise ValueError(f"map_assemblies_gen4.csv : plan natif absent : {family}:{part.source}")
        groups.setdefault(part.plan, []).append(part)
    translations = {}
    for plan, members in groups.items():
        _validate_members(maps, members)
        width = max(part.x + maps[part.source].width for part in members)
        height = max(part.y + maps[part.source].height for part in members)
        if max(width, height) > 8192 or plan in maps:
            raise ValueError(f"map_assemblies_gen4.csv : assemblage trop grand ou déjà défini : {plan}")
        first = members[0]
        parent = MapRow(
            plan,
            first.number,
            first.name,
            None,
            0,
            0,
            width,
            height,
            level_count(width, height),
            origin=maps[first.source].origin,
        )
        _assemble_tiles(output, maps, members, parent)
        data.maps.append(parent)
        sources = {part.source: part for part in members}
        for row in list(maps.values()):
            part = sources.get(row.parent or row.const)
            if part is None:
                continue
            translations[row.const] = (part.x, part.y)
            row.parent = plan
            row.x += part.x
            row.y += part.y
            row.level_count = 0
    _translate_content(data, translations)
    _write_catalog(output, data.maps)
    coordinates = {const: {"native": native[const], "offset": offset} for const, offset in translations.items()}
    (output / "assemblies.json").write_text(
        json.dumps(coordinates, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )


def _validate_members(maps: dict[str, MapRow], members: list[AssemblyPart]) -> None:
    numbers = {row.number for row in maps.values()}
    if members[0].number in numbers:
        raise ValueError(f"map_assemblies_gen4.csv : numéro déjà utilisé : {members[0].number}")
    for index, part in enumerate(members):
        current = maps[part.source]
        for other in members[:index]:
            previous = maps[other.source]
            horizontal = part.x < other.x + previous.width and other.x < part.x + current.width
            vertical = part.y < other.y + previous.height and other.y < part.y + current.height
            if horizontal and vertical:
                raise ValueError(f"map_assemblies_gen4.csv : {part.source} recouvre {other.source}")


def _assemble_tiles(output: Path, maps: dict[str, MapRow], members: list[AssemblyPart], parent: MapRow) -> None:
    target = output / identifier(parent.const)
    top = target / str(parent.level_count - 1)
    top.mkdir(parents=True, exist_ok=True)
    for part in members:
        source = maps[part.source]
        folder = output / identifier(source.const) / str(source.level_count - 1)
        files = sorted(folder.glob("*.webp"))
        if not files or len(files) > 1024:
            raise ValueError(f"{folder} : nombre de tuiles invalide : {len(files)}")
        for path in files:
            row, column = (int(value) for value in path.stem.split("_"))
            destination = top / f"{row + part.y // TILE_SIZE}_{column + part.x // TILE_SIZE}.webp"
            with Image.open(path) as image:
                image.save(destination, "WEBP", lossless=True, exact=True)
    write_pyramid(target, (parent.width, parent.height))


def _translate_content(data: GameMapData, translations: dict[str, tuple[int, int]]) -> None:
    for obj in [*data.objects, *data.warps, *data.spots]:
        dx, dy = translations.get(obj.map_const, (0, 0))
        obj.x += dx
        obj.y += dy
    for warp in data.warps:
        dx, dy = translations.get(warp.target or "", (0, 0))
        if warp.target_x is not None and warp.target_y is not None:
            warp.target_x += dx
            warp.target_y += dy
    by_identifier = {identifier(const): offset for const, offset in translations.items()}
    data.coordinate_offsets = by_identifier
    data.terrain = {
        key: frozenset((x + dx, y + dy) for x, y in points)
        for key, points in data.terrain.items()
        for dx, dy in (by_identifier.get(key[0], (0, 0)),)
    }


def _write_catalog(output: Path, maps: list[MapRow]) -> None:
    with (output / "catalog.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, tuple(asdict(maps[0])), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(asdict(row) for row in maps)
