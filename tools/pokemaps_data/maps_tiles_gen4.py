"""Tuiles DS rendues par cadres bornés ; pyramide construite sans image régionale en mémoire."""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .maps_layout_gen4 import BLOCK_PX, MatrixDisplay, camera_cotangent
from .maps_raster_gen4 import ONE, RasterCanvas
from .maps_render import TILE_SIZE, level_count
from .maps_render_gen4 import BlockRender, Gen4Renderer, RasterTriangle
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_map_models import Gen4Header


@dataclass(frozen=True)
class BlockSource:
    request: BlockRender
    offset: tuple[int, int]
    bounds: tuple[int, int, int, int]


@dataclass(frozen=True)
class Atlas:
    display: MatrixDisplay
    bounds: tuple[int, int, int, int]
    sources: tuple[BlockSource, ...]
    base: str | None = None
    replacement: tuple[tuple[int, int, int, int], ...] = ()

    @property
    def size(self) -> tuple[int, int]:
        return self.bounds[2] - self.bounds[0], self.bounds[3] - self.bounds[1]


@dataclass(frozen=True)
class TileJob:
    root: Path
    versions: tuple[tuple[str, str], ...]
    output: Path
    origin: tuple[int, int]
    size: tuple[int, int]
    tile: tuple[int, int]
    sources: tuple[BlockSource, ...]
    ceiling: int | None = None


def prepare_atlas(renderer: Gen4Renderer, display: MatrixDisplay, headers: dict[int, Gen4Header]) -> Atlas:
    sources = []
    for block in display.blocks:
        header = headers[block.header]
        request = BlockRender(block.block, header.area, camera_cotangent(renderer.repo, header), block.altitude)
        offset = (block.column * BLOCK_PX, block.row * BLOCK_PX)
        prepared = _prepare_source(renderer, display, request, block.column, block.row, headers)
        request, geometry = prepared
        points = [
            (
                v.position[0] // ONE + offset[0],
                (v.position[2] - v.position[1] * request.cotangent // ONE) // ONE + offset[1],
            )
            for triangle, _ in geometry
            for v in triangle
        ]
        if not points:
            continue
        bounds = (
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points) + 1,
            max(p[1] for p in points) + 1,
        )
        sources.append(BlockSource(request, offset, bounds))
    if not sources:
        raise ValueError(f"{display.const} : assemblage sans géométrie visible")
    raw = (
        min(display.bounds[0], min(s.bounds[0] for s in sources)),
        min(display.bounds[1], min(s.bounds[1] for s in sources)),
        max(display.bounds[2], max(s.bounds[2] for s in sources)),
        max(display.bounds[3], max(s.bounds[3] for s in sources)),
    )
    bounds = tuple(
        (value // TILE_SIZE if i < 2 else math.ceil(value / TILE_SIZE)) * TILE_SIZE for i, value in enumerate(raw)
    )
    if max(bounds[2] - bounds[0], bounds[3] - bounds[1]) > 32768:
        raise ValueError(f"{display.const} : assemblage DS trop grand : {bounds}")
    return Atlas(display, bounds, tuple(sources))


def _prepare_source(
    renderer: Gen4Renderer,
    display: MatrixDisplay,
    request: BlockRender,
    x: int,
    y: int,
    headers: dict[int, Gen4Header],
) -> tuple:
    matrix = renderer.repo.matrices[display.matrix]
    if matrix.headers is None or matrix.headers[y][x] not in (0, 1):
        return request, renderer.prepare_block(request)
    # Une matrice ne stocke pas la zone des blocs de remplissage. Parmi les voisins, seuls les jeux
    # capables de lier toutes les ressources du bloc sont candidats ; distance et ordre fixent le choix.
    candidates = sorted(display.blocks, key=lambda b: (abs(b.column - x) + abs(b.row - y), b.row, b.column))
    areas = set()
    errors = []
    for candidate in candidates:
        header = headers[candidate.header]
        if header.area in areas:
            continue
        areas.add(header.area)
        alternative = BlockRender(request.block, header.area, camera_cotangent(renderer.repo, header), request.altitude)
        try:
            return alternative, renderer.prepare_block(alternative)
        except ValueError as error:
            errors.append(str(error))
    raise ValueError(f"{display.const} bloc ({x}, {y}) : aucune zone compatible : {errors}")


def jobs(repo: Gen4PretRepo, atlas: Atlas, output: Path, ceiling: int | None = None) -> tuple[TileJob, ...]:
    result = []
    width, height = atlas.size
    for y in range(0, height, BLOCK_PX):
        for x in range(0, width, BLOCK_PX):
            origin = (x + atlas.bounds[0], y + atlas.bounds[1])
            size = (min(BLOCK_PX, width - x), min(BLOCK_PX, height - y))
            box = (*origin, origin[0] + size[0], origin[1] + size[1])
            if atlas.replacement and not any(overlaps(box, changed) for changed in atlas.replacement):
                continue
            sources = tuple(s for s in atlas.sources if overlaps(s.bounds, box))
            if sources:
                result.append(
                    TileJob(
                        repo.root,
                        repo.versions,
                        output,
                        origin,
                        size,
                        (x // TILE_SIZE, y // TILE_SIZE),
                        sources,
                        ceiling,
                    )
                )
    return tuple(result)


def overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def render_job(job: TileJob, renderer: Gen4Renderer | None = None) -> int:
    renderer = renderer or Gen4Renderer(Gen4PretRepo(job.root, job.versions))
    prepared = [(source, renderer.prepare_block(source.request)) for source in job.sources]
    key = renderer.frames.key(job, prepared)
    image = renderer.frames.read(key)
    if image is None:
        image = _render_frame(job, prepared)
        renderer.frames.write(key, image)
    else:
        renderer.frame_cache_hits += 1
    return _write_frame(job, image)


def _render_frame(job: TileJob, prepared: list[tuple[BlockSource, tuple[RasterTriangle, ...]]]) -> Image.Image:
    canvas = RasterCanvas(job.origin, job.size, 0, job.ceiling)
    for translucent in (False, True):
        for source, triangles in prepared:
            canvas.ceiling = source.request.ceiling if source.request.ceiling is not None else job.ceiling
            for vertices, material in triangles:
                if (material.alpha < 31) == translucent:
                    canvas.triangle(vertices, material, source.offset, source.request.cotangent)
    return canvas.image()


def _write_frame(job: TileJob, image: Image.Image) -> int:
    count = 0
    for y in range(0, image.height, TILE_SIZE):
        for x in range(0, image.width, TILE_SIZE):
            tile = image.crop((x, y, x + TILE_SIZE, y + TILE_SIZE))
            if tile.getextrema()[3][1] == 0:
                continue
            path = job.output / f"{job.tile[1] + y // TILE_SIZE}_{job.tile[0] + x // TILE_SIZE}.webp"
            path.parent.mkdir(parents=True, exist_ok=True)
            tile.save(path, "WEBP", lossless=True, method=4, exact=True)
            count += 1
    return count


def render_batch(batch: tuple[TileJob, ...]) -> tuple[int, int]:
    if not batch or len(batch) > 8:
        raise ValueError(f"Lot de rendu DS invalide : {len(batch)}")
    renderer = Gen4Renderer(Gen4PretRepo(batch[0].root, batch[0].versions))
    if any(job.root != batch[0].root or job.versions != batch[0].versions for job in batch):
        raise ValueError("Un lot de rendu DS mélange les sources de plusieurs jeux")
    count = sum(render_job(job, renderer) for job in batch)
    return count, renderer.frame_cache_hits


def write_pyramid(output: Path, size: tuple[int, int]) -> int:
    levels = level_count(*size)
    count = 0
    for level in range(levels - 2, -1, -1):
        children = output / str(level + 1)
        parents = {(int(p.stem.split("_")[0]) // 2, int(p.stem.split("_")[1]) // 2) for p in children.glob("*.webp")}
        for row, column in sorted(parents):
            image = Image.new("RGBA", (TILE_SIZE * 2, TILE_SIZE * 2))
            for dy in range(2):
                for dx in range(2):
                    path = children / f"{row * 2 + dy}_{column * 2 + dx}.webp"
                    if path.is_file():
                        with Image.open(path) as tile:
                            image.paste(tile, (dx * TILE_SIZE, dy * TILE_SIZE))
            image = image.resize((TILE_SIZE, TILE_SIZE), Image.Resampling.BOX)
            target = output / str(level) / f"{row}_{column}.webp"
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "WEBP", lossless=True, method=4, exact=True)
            count += 1
    return count


def remove_displays(staging: Path, consts: tuple[str, ...]) -> None:
    from .maps_layout import identifier

    for const in consts:
        folder = staging / identifier(const)
        if folder.is_symlink() or folder.resolve().parent != staging.resolve():
            raise ValueError(f"Dossier de scène DS invalide : {folder}")
        if folder.is_dir():
            shutil.rmtree(folder)
