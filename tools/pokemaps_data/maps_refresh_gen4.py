"""Réexport atomique des catalogues DS sans refaire les images."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .games import GEN4_GAMES
from .maps_catalog_gen4 import write_catalog
from .maps_gen4 import _report
from .maps_layout_gen4 import displays, selected_headers
from .maps_lower_gen4 import _skipped_levels
from .maps_tiles_gen4 import Atlas, remove_displays
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_source import read_json
from .sources import PRET_COMMITS, fetch_pret
from .validate_maps_gen4 import check_inventory, validate_catalog, write_inventory


def refresh_catalogs(cache: Path, output: Path) -> None:
    if not output.is_dir() or output.is_symlink() or output.name != "sinnoh-maps":
        raise ValueError(f"Aperçu DS généré attendu : {output}")
    report_path = output / "generation-report.json"
    reports = json.loads(report_path.read_text(encoding="utf-8"))
    updated = []
    for game in GEN4_GAMES:
        started = time.perf_counter()
        folder = output / game.version_group
        check_inventory(folder)
        repo = Gen4PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        metadata = read_json(folder / "matrices.json")
        if metadata["commit"] != PRET_COMMITS[game.pret_repo]:
            raise ValueError(f"{folder} : sources modifiées ; relancer --sinnoh-maps-only")
        headers = selected_headers(repo)
        if {header["index"] for header in metadata["headers"]} != headers.keys():
            raise ValueError(f"{folder} : sélection modifiée ; relancer --sinnoh-maps-only")
        atlases = _catalog_atlases(repo, metadata)
        with TemporaryDirectory(prefix=".catalog-", dir=output.resolve()) as temporary:
            staging = Path(temporary) / game.version_group
            shutil.copytree(folder, staging)
            _prune_levels(repo, metadata, staging)
            write_catalog(repo, headers, atlases, staging)
            validate_catalog(staging)
            write_inventory(staging)
            check_inventory(staging)
            folder.rename(output / f"{game.version_group}.previous-{time.time_ns()}")
            staging.rename(folder)
        previous = next(report for report in reports if report["version_group"] == game.version_group)
        report = _report(game, folder, time.perf_counter() - previous["seconds"], previous["workers"])
        report["seconds"] = previous["seconds"]
        report["catalog_seconds"] = round(time.perf_counter() - started, 2)
        updated.append(report)
    report_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prune_levels(repo: Gen4PretRepo, metadata: dict, staging: Path) -> None:
    skipped = _skipped_levels(repo)
    headers = {header["index"]: header["constant"] for header in metadata["headers"]}
    bases = {
        display["const"]
        for display in metadata["displays"]
        if display["base"] is None and any(headers[index] in skipped for index in display["headers"])
    }
    removed = tuple(display["const"] for display in metadata["displays"] if display["base"] in bases)
    if not removed:
        return
    remove_displays(staging, removed)
    metadata["displays"] = [display for display in metadata["displays"] if display["const"] not in removed]
    (staging / "matrices.json").write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    path = staging / "levels.json"
    levels = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps([level for level in levels if level["display"] not in bases], sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _catalog_atlases(repo: Gen4PretRepo, metadata: dict) -> tuple[Atlas, ...]:
    layouts = {layout.const: layout for layout in displays(repo, selected_headers(repo))}
    native = {display["const"]: display for display in metadata["displays"] if display["base"] is None}
    if layouts.keys() != native.keys():
        raise ValueError(f"{repo.variant} : plans modifiés ; relancer --sinnoh-maps-only")
    result = []
    for const, layout in layouts.items():
        source = native[const]
        if source["matrix"] != layout.matrix or tuple(source["headers"]) != layout.headers:
            raise ValueError(f"{const} : matrice ou en-têtes modifiés ; relancer --sinnoh-maps-only")
        expected = {(block.column * 512, block.row * 512, block.block) for block in layout.blocks}
        actual = {(*block["offset"], block["request"]["block"]) for block in source["blocks"]}
        if actual != expected:
            raise ValueError(f"{const} : sélection des blocs modifiée ; relancer --sinnoh-maps-only")
        matrix = repo.matrices[layout.matrix]
        for block in source["blocks"]:
            column, row = (value // 512 for value in block["offset"])
            if matrix.blocks[row][column] != block["request"]["block"]:
                raise ValueError(f"{const} : bloc modifié ; relancer --sinnoh-maps-only")
        result.append(Atlas(layout, tuple(source["bounds"]), ()))
    return tuple(result)
