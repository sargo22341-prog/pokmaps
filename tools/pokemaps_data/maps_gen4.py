"""Génération explicite des deux familles de cartes DS, sans activation dans la base Android."""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from .games import GEN4_GAMES, Game
from .maps_catalog_gen4 import write_catalog
from .maps_layout import identifier
from .maps_layout_gen4 import displays, selected_headers
from .maps_lower_gen4 import lower_atlases
from .maps_render import level_count
from .maps_render_gen4 import Gen4Renderer
from .maps_tiles_gen4 import Atlas, TileJob, jobs, prepare_atlas, render_batch, write_pyramid
from .pret_gen4 import Gen4PretRepo
from .sources import PRET_COMMITS, fetch_pret
from .validate_maps_gen4 import validate_catalog, write_inventory

_MAX_JOBS = 20_000
_BUILD_TIMEOUT_SECONDS = 7200


def build_gen4_maps(cache: Path, output: Path, workers: int = 4) -> None:
    if not 1 <= workers <= 8:
        raise ValueError("Le rendu DS accepte de 1 à 8 processus")
    parent = output.parent.resolve()
    if output.is_symlink() or output.resolve().parent != parent or output.name != "sinnoh-maps":
        raise ValueError(f"Dossier de cartes DS invalide : {output}")
    parent.mkdir(parents=True, exist_ok=True)
    # Vérifier les deux familles avant le premier rendu coûteux.
    prepared = []
    for game in GEN4_GAMES:
        repo = Gen4PretRepo(fetch_pret(cache, game.pret_repo), game.pret_versions)
        headers = selected_headers(repo)
        prepared.append((repo, headers, _prepare(repo, headers)))
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    for game, source in zip(GEN4_GAMES, prepared, strict=True):
        with TemporaryDirectory(prefix=".sinnoh-maps-", dir=parent) as temporary:
            staging = Path(temporary) / game.version_group
            reports.append(_build_game(staging, game, workers, source))
            destination = output / game.version_group
            if destination.exists():
                destination.rename(output / f"{game.version_group}.previous-{time.time_ns()}")
            staging.rename(destination)
        report = output / "generation-report.json"
        report.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_game(output: Path, game: Game, workers: int, source: tuple) -> dict:
    start = time.perf_counter()
    repo, headers, base_atlases = source
    output.mkdir(parents=True, exist_ok=True)
    lower, surfaces = lower_atlases(repo, base_atlases)
    all_atlases = base_atlases + lower
    pending = tuple(
        job
        for atlas in all_atlases
        for job in jobs(repo, atlas, output / identifier(atlas.display.const) / str(level_count(*atlas.size) - 1))
    )
    _render(pending, workers)
    for atlas in all_atlases:
        write_pyramid(output / identifier(atlas.display.const), atlas.size)
    _write_matrices(repo, headers, all_atlases, surfaces, output)
    write_catalog(repo, headers, base_atlases, output)
    validate_catalog(output)
    write_inventory(output)
    return _report(game, output, start, workers)


def _prepare(repo: Gen4PretRepo, headers: dict) -> tuple[Atlas, ...]:
    renderer = Gen4Renderer(repo)
    layouts = displays(repo, headers)
    print(f"{repo.variant} : préparation de {len(layouts)} assemblages…", flush=True)
    atlases = []
    for index, display in enumerate(layouts):
        atlases.append(prepare_atlas(renderer, display, headers))
        if index % 50 == 0:
            print(f"  géométrie {index + 1}/{len(layouts)}", flush=True)
    return tuple(atlases)


def _write_matrices(
    repo: Gen4PretRepo, headers: dict, atlases: tuple[Atlas, ...], surfaces: list[dict], output: Path
) -> None:
    catalog = {
        "version_group": repo.variant,
        "commit": PRET_COMMITS["pokeplatinum" if repo.platinum else "pokediamond"],
        "headers": [asdict(header) for header in headers.values()],
        "displays": [
            {
                "const": a.display.const,
                "matrix": a.display.matrix,
                "headers": a.display.headers,
                "bounds": a.bounds,
                "size": a.size,
                "level_count": level_count(*a.size),
                "base": a.base,
                "replacement": a.replacement,
                "blocks": [asdict(source) for source in a.sources],
            }
            for a in atlases
        ],
    }
    (output / "matrices.json").write_text(
        json.dumps(catalog, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "levels.json").write_text(json.dumps(surfaces, sort_keys=True) + "\n", encoding="utf-8")


def _report(game: Game, output: Path, start: float, workers: int) -> dict:
    files = [path for path in output.rglob("*") if path.is_file()]
    tiles = [path for path in files if path.suffix == ".webp" and path.parent.name.isdecimal()]
    sizes = [(p.relative_to(output).as_posix(), p.stat().st_size) for p in files]
    report = {
        "version_group": game.version_group,
        "tiles": len(tiles),
        "tile_bytes": sum(path.stat().st_size for path in tiles),
        "sprites": sum(path.parent.name == "sprites" for path in files),
        "bytes": sum(n for _, n in sizes),
        "seconds": round(time.perf_counter() - start, 2),
        "workers": workers,
        "assets_over_5_mib": [(p, n) for p, n in sizes if n > 5 * 1024 * 1024],
    }
    print(report, flush=True)
    return report


def _render(pending: tuple[TileJob, ...], workers: int) -> None:
    if not pending or len(pending) > _MAX_JOBS:
        raise ValueError(f"Nombre de cadres DS invalide : {len(pending)}")
    print(f"Rendu de {len(pending)} cadres avec {workers} processus (CPU : {os.cpu_count()})…", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        batches = tuple(pending[index : index + 8] for index in range(0, len(pending), 8))
        futures = [pool.submit(render_batch, batch) for batch in batches]
        try:
            for index, future in enumerate(as_completed(futures, timeout=_BUILD_TIMEOUT_SECONDS), 1):
                future.result()
                if index % 5 == 0 or index == len(futures):
                    print(f"  lots rendus {index}/{len(futures)}", flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
