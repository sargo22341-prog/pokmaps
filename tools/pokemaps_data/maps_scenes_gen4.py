"""Réexport ciblé du décor moteur et des calques de hauteur, depuis un aperçu DS validé."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .games import GEN4_GAMES
from .maps_catalog_gen4 import write_catalog
from .maps_dynamic_gen4 import DynamicProps
from .maps_gen4 import _prepare, _render, _report, _write_matrices
from .maps_layout import identifier
from .maps_layout_gen4 import selected_headers
from .maps_lower_gen4 import lower_atlases
from .maps_refresh_gen4 import _catalog_atlases
from .maps_render import level_count
from .maps_tiles_gen4 import Atlas, jobs, remove_displays, write_pyramid
from .pret_gen4 import Gen4PretRepo
from .sources import PRET_COMMITS, fetch_pret
from .validate_maps_gen4 import check_inventory, validate_catalog, write_inventory


def rebuild_scenes(cache: Path, output: Path, workers: int) -> None:
    if output.name != "sinnoh-maps" or output.is_symlink() or not 1 <= workers <= 8:
        raise ValueError(f"Aperçu DS ou nombre de processus invalide : {output}, {workers}")
    reports = json.loads((output / "generation-report.json").read_text(encoding="utf-8"))
    updated = []
    for game in GEN4_GAMES:
        started = time.perf_counter()
        folder = output / game.version_group
        check_inventory(folder)
        repo = Gen4PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        metadata = json.loads((folder / "matrices.json").read_text(encoding="utf-8"))
        if metadata["commit"] != PRET_COMMITS[game.pret_repo]:
            raise ValueError(f"{folder} : sources modifiées ; relancer --sinnoh-maps-only")
        _catalog_atlases(repo, metadata)
        headers = selected_headers(repo)
        base = _prepare(repo, headers)
        lower, surfaces = lower_atlases(repo, base)
        dynamic = DynamicProps(repo).by_block.keys()
        affected = tuple(a for a in base if any((s.request.block, s.request.area) in dynamic for s in a.sources))
        with TemporaryDirectory(prefix=".scenes-", dir=output.resolve()) as temporary:
            staging = Path(temporary) / game.version_group
            shutil.copytree(folder, staging)
            old = tuple(display["const"] for display in metadata["displays"] if display["base"])
            remove_displays(staging, old + tuple(a.display.const for a in affected))
            _render_displays(repo, staging, affected + lower, workers)
            _write_matrices(repo, headers, base + lower, surfaces, staging)
            write_catalog(repo, headers, base, staging)
            validate_catalog(staging)
            write_inventory(staging)
            check_inventory(staging)
            folder.rename(output / f"{game.version_group}.previous-{time.time_ns()}")
            staging.rename(folder)
        previous = next(report for report in reports if report["version_group"] == game.version_group)
        report = _report(game, folder, started, workers)
        report["scenes_seconds"] = report["seconds"]
        report["seconds"] += previous["seconds"]
        updated.append(report)
        (output / "generation-report.json").write_text(
            json.dumps(updated + reports[len(updated) :], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def _render_displays(repo: Gen4PretRepo, output: Path, atlases: tuple[Atlas, ...], workers: int) -> None:
    pending = tuple(
        job
        for atlas in atlases
        for job in jobs(repo, atlas, output / identifier(atlas.display.const) / str(level_count(*atlas.size) - 1))
    )
    _render(pending, workers)
    for atlas in atlases:
        write_pyramid(output / identifier(atlas.display.const), atlas.size)
