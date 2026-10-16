"""Calques de remplacement des surfaces basses, alignés sur leur assemblage d'origine."""

from __future__ import annotations

import csv
from dataclasses import replace

from .maps_levels_gen4 import LowerSurface, lower_surfaces
from .maps_tiles_gen4 import Atlas
from .pret_gen4 import Gen4PretRepo
from .sources import DATA_DIR


def lower_atlases(repo: Gen4PretRepo, atlases: tuple[Atlas, ...]) -> tuple[tuple[Atlas, ...], list[dict]]:
    cache: dict[tuple[int, int], tuple[LowerSurface, ...]] = {}
    result, records = [], []
    skipped = _skipped_levels(repo)
    for atlas in atlases:
        if any(repo.headers[index].constant in skipped for index in atlas.display.headers):
            continue
        for source in atlas.sources:
            request = source.request
            key = (request.block, request.altitude)
            if key not in cache:
                cache[key] = lower_surfaces(repo.land_block(request.block), request.altitude)
        count = max(len(cache[s.request.block, s.request.altitude]) for s in atlas.sources)
        for level in range(count):
            layer, rows = _lower_atlas(atlas, cache, level)
            result.append(layer)
            records.extend(rows)
    return tuple(result), records


def _skipped_levels(repo: Gen4PretRepo) -> set[str]:
    known = {header.constant for header in repo.headers.values()}
    result = set()
    with (DATA_DIR / "map_level_skips_gen4.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["family"] != repo.variant:
                continue
            if row["map"] not in known or row["map"] in result or not row["reason"].strip():
                raise ValueError(f"map_level_skips_gen4.csv : exclusion de niveau invalide : {row}")
            result.add(row["map"])
    return result


def _lower_atlas(atlas: Atlas, cache: dict, level: int) -> tuple[Atlas, list[dict]]:
    sources, boxes, records = [], [], []
    for source in atlas.sources:
        request = source.request
        surfaces = cache[request.block, request.altitude]
        if level < len(surfaces):
            lower = surfaces[level]
            boxes.append(source.bounds)
            source = replace(source, request=replace(request, ceiling=lower.ceiling))
            records.append(
                {
                    "display": atlas.display.const,
                    "level": level,
                    "block": request.block,
                    "offset": source.offset,
                    "ceiling": lower.ceiling,
                    "cells": lower.cells,
                }
            )
        sources.append(source)
    suffix = "_LOWER" if level == 0 else f"_LOWER_{level + 1}"
    display = replace(atlas.display, const=atlas.display.const + suffix)
    return Atlas(display, atlas.bounds, tuple(sources), atlas.display.const, tuple(boxes)), records
