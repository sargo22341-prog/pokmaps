"""Catalogues DS français, événements et sprites ; indépendants de l'activation Android."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .maps import MapRow, read_map_names
from .maps_common_gen4 import common_passages
from .maps_dynamic_gen4 import DynamicProps
from .maps_layout import read_layout_curation
from .maps_passages_gen4 import scripted_passages, warps
from .maps_render import level_count
from .maps_sprites_gen4 import read_field_sprites
from .maps_tiles_gen4 import Atlas
from .maps_travel_gen4 import distortion_connections, fly_destinations, turnback_connections, underground_connections
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_map_models import Gen4Header


def _map_rows(repo: Gen4PretRepo, headers: dict[int, Gen4Header], atlases: tuple[Atlas, ...]) -> list[MapRow]:
    names = read_map_names()[repo.variant]
    curation = read_layout_curation()
    plans = {part.plan: part for part in curation.plans if part.family == repo.variant}
    origins = {parent.map: parent.parent for parent in curation.parents if parent.family == repo.variant}
    rows = []
    for atlas in atlases:
        const = atlas.display.const
        first = headers[atlas.display.headers[0]]
        plan = plans.get(const)
        name = "Sinnoh" if const == "SINNOH" else (plan.name if plan else names[const])
        number = 994 if const == "SINNOH" else (plan.number if plan else first.index)
        rows.append(
            MapRow(
                const,
                number,
                name,
                None,
                0,
                0,
                *atlas.size,
                level_count(*atlas.size),
                const == "SINNOH",
                origin=origins.get(first.constant),
            )
        )
        for index in atlas.display.headers:
            header = headers[index]
            if header.constant == const:
                continue
            x, y, width, height = _region_rectangle(repo, header, atlas)
            rows.append(
                MapRow(
                    header.constant,
                    header.index,
                    names[header.constant],
                    const,
                    x,
                    y,
                    width,
                    height,
                    0,
                    origin=origins.get(header.constant),
                )
            )
    return rows


def write_catalog(repo: Gen4PretRepo, headers: dict[int, Gen4Header], atlases: tuple[Atlas, ...], output: Path) -> None:
    _write_tsv(output / "catalog.tsv", [asdict(row) for row in _map_rows(repo, headers, atlases)])
    passages = (
        warps(repo, headers)
        + scripted_passages(repo, headers)
        + fly_destinations(repo)
        + distortion_connections(repo)
        + turnback_connections(repo)
        + common_passages(repo)
        + underground_connections(repo)
    )
    _write_tsv(output / "passages.tsv", [asdict(passage) for passage in passages])
    events = {header.constant: asdict(repo.events[header.events]) for header in headers.values()}
    _write_json(output / "events.json", events)
    _write_json(output / "dynamic-props.json", {"props": [asdict(prop) for prop in DynamicProps(repo).placements]})
    _write_sprites(repo, headers, output)


def _region_rectangle(repo: Gen4PretRepo, header: Gen4Header, atlas: Atlas) -> tuple[int, int, int, int]:
    matrix = repo.matrices[header.matrix]
    cells = [
        (x, y)
        for y, row in enumerate(matrix.blocks)
        for x, block in enumerate(row)
        if block != 0xFFFF and (matrix.headers is None or matrix.headers[y][x] == header.index)
    ]
    if not cells:
        raise ValueError(f"{header.constant} : région sans bloc")
    left, top = min(x for x, _ in cells) * 512, min(y for _, y in cells) * 512
    width = (max(x for x, _ in cells) + 1) * 512 - left
    height = (max(y for _, y in cells) + 1) * 512 - top
    return left - atlas.bounds[0], top - atlas.bounds[1], width, height


def _write_sprites(repo: Gen4PretRepo, headers: dict[int, Gen4Header], output: Path) -> None:
    used = {obj.graphics for header in headers.values() for obj in repo.events[header.events].object_events}
    sprites = read_field_sprites(repo, used)
    folder = output / "sprites"
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for sprite in sprites:
        sprite.image.save(folder / f"{sprite.graphics}.webp", "WEBP", lossless=True, exact=True)
        rows.append({"graphics": sprite.graphics, "source": sprite.source, "size": sprite.image.size})
    without_texture = sorted(used - {sprite.graphics for sprite in sprites})
    _write_json(
        output / "sprites.json",
        {
            "sprites": rows,
            "without_texture": [
                {
                    "graphics": value,
                    "kind": "variable" if 100 <= value <= 115 else "model",
                    "note": "Apparence choisie par le scénario."
                    if 100 <= value <= 115
                    else "Objet de terrain à modèle 3D, sans image de personnage.",
                }
                for value in without_texture
            ],
        },
    )


def _write_tsv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"{path} : catalogue DS vide")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, tuple(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
