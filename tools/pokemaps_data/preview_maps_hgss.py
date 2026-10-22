"""Atlas HGSS et lot témoin, remplacés seulement après validation des deux cartouches."""

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from .maps_render import DisplayMap, level_count, write_tiles
from .maps_render_hgss import HgssRenderer, camera_cotangent
from .pret_gen4_land import FX_ONE
from .pret_hgss_maps import PROOF_MAPS, HgssHeader, HgssMapRepo
from .sources import HGSS_PRET_COMMIT
from .validate_hgss_maps import surface_grid, validate_proof, validate_sources


def _json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def build_hgss_maps(cache: Path, output: Path, workers: int = 4) -> None:
    started = time.perf_counter()
    root = (cache / "hgss-qualification").resolve()
    target = (output / "hgss-maps").resolve()
    assets = Path(__file__).resolve().parents[2] / "app/src/main/assets"
    if any(target.is_relative_to(p.resolve()) or p.resolve().is_relative_to(target) for p in (root, assets)):
        raise ValueError("L'aperçu HGSS doit rester séparé des sources et assets distribués")
    sources = validate_sources(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".hgss-maps-", dir=target.parent) as temporary:
        staging = Path(temporary) / "hgss-maps"
        staging.mkdir()
        reports = [_version(root, staging, version) for version in ("heartgold", "soulsilver")]
        if reports[0]["maps"] != reports[1]["maps"] or reports[0]["proof"] != reports[1]["proof"]:
            raise ValueError("HGSS : géométrie ou rendu des deux cartouches différents sur le lot témoin")
        _json(
            staging / "proof.json",
            {
                "commit": HGSS_PRET_COMMIT,
                "sources": sources,
                "versions": reports,
                "units": {"block_tiles": 32, "tile_units": 16, "fx_one": FX_ONE, "altitude_units": 8},
            },
        )
        from .preview_johto_hgss import build_johto

        build_johto(root, staging, cache / "map-renders/hgss-johto", workers)
        build_johto(root, staging, cache / "map-renders/hgss-atlas", workers, "atlas")
        _write_inventory(staging)
        if target.exists():
            target.rename(Path(temporary) / "previous")
        try:
            staging.rename(target)
        except OSError:
            previous = Path(temporary) / "previous"
            if previous.exists():
                previous.rename(target)
            raise
    print(f"Cartes HGSS validées : {target} ({time.perf_counter() - started:.2f} s, preuve, Johto et atlas)")


def _version(root: Path, output: Path, version: str) -> dict:
    repo = HgssMapRepo(root, version)
    renderer = HgssRenderer(repo)
    folder = output / version
    folder.mkdir()
    proof = validate_proof(repo)
    maps = []
    for name in PROOF_MAPS:
        header = next(h for h in repo.headers.values() if h.constant == f"MAP_{name}")
        maps.append(_map(renderer, header, folder))
    return {"version": version, "maps": maps, "proof": proof}


def _map(renderer: HgssRenderer, header: HgssHeader, output: Path) -> dict:
    folder = output / header.constant.removeprefix("MAP_").lower()
    folder.mkdir()
    image, origin = renderer.render(header)
    cells = surface_grid(renderer.repo, header)
    events = renderer.repo.events(header)
    native = {
        "header": asdict(header),
        "blocks": renderer.repo.blocks(header),
        "events": asdict(events),
        "cells": cells,
    }
    _json(folder / "native.json", native)
    image.save(folder / "map.png")
    display = DisplayMap(header.constant, *image.size, level_count(*image.size), image)
    tiles = write_tiles(display, folder / "tiles")
    actor = _review(renderer, header, image, origin, cells, folder)
    lower = _lower(renderer, header, cells, folder)
    print(f"  {renderer.repo.version} {header.constant} : {tiles} tuiles", flush=True)
    return {
        "header": header.index,
        "origin_pixels": origin,
        "size": image.size,
        "tiles": tiles,
        "pixels_sha256": _digest(image),
        "native_sha256": hashlib.sha256(json.dumps(native).encode()).hexdigest(),
        "actor": actor,
        "lower": lower,
    }


def _point(x: int, z: int, y: int, origin: tuple[int, int], cotangent: int) -> tuple[int, int]:
    return x * 16 + 8 - origin[0], z * 16 + 8 - y * cotangent // FX_ONE // FX_ONE - origin[1]


def _review(
    renderer: HgssRenderer,
    header: HgssHeader,
    image: Image.Image,
    origin: tuple[int, int],
    cells: list[dict],
    folder: Path,
) -> dict:
    events = renderer.repo.events(header)
    cotangent = camera_cotangent(renderer.repo.root, header)
    lookup = {(cell["x"], cell["z"]): cell for cell in cells}
    overlay = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(overlay)
    for cell in cells:
        if cell["attribute"] & 0x8000 and cell["heights"]:
            x, z = _point(cell["x"], cell["z"], max(cell["heights"]), origin, cotangent)
            draw.rectangle((x - 7, z - 7, x + 7, z + 7), fill=(255, 40, 40, 80))
    Image.alpha_composite(image, overlay).save(folder / "collision.png")
    review = image.copy()
    draw = ImageDraw.Draw(review)
    for index, warp in enumerate(events.warps):
        cell = lookup.get((warp.x, warp.z))
        if cell is None or not cell["heights"]:
            raise ValueError(f"{header.constant} : passage {index} hors du terrain")
        x, z = _point(warp.x, warp.z, min(cell["heights"]), origin, cotangent)
        draw.ellipse((x - 7, z - 7, x + 7, z + 7), outline="cyan", width=2)
        draw.text(
            (x + 8, z), f"{index} > {warp.destination}:{warp.anchor}", fill="cyan", stroke_width=1, stroke_fill="black"
        )
    actor = _place_actor(renderer, header, review, origin, lookup)
    review.save(folder / "review.png")
    return actor


def _place_actor(
    renderer: HgssRenderer,
    header: HgssHeader,
    review: Image.Image,
    origin: tuple[int, int],
    lookup: dict,
) -> dict:
    events = renderer.repo.events(header)
    cotangent = camera_cotangent(renderer.repo.root, header)
    actor = next(
        (a for a in events.actors if a.script != "0" and a.sprite in renderer.sprite_models and (a.x, a.z) in lookup),
        None,
    )
    if actor is None:
        raise ValueError(f"{header.constant} : acteur de preuve absent")
    frame, source = renderer.actor_image(actor.sprite)
    surface = lookup[(actor.x, actor.z)]["heights"]
    if not surface:
        raise ValueError(f"{header.constant} : acteur sans surface de terrain")
    y = min(surface, key=lambda height: abs(height - actor.y))
    x, z = _point(actor.x, actor.z, y, origin, cotangent)
    review.alpha_composite(frame, (x - frame.width // 2, z - frame.height))

    return {"native": asdict(actor), "sprite_source": source, "surface_fx32": y, "frame": "face"}


def _lower(renderer: HgssRenderer, header: HgssHeader, cells: list[dict], folder: Path) -> dict | None:
    if header.constant != "MAP_ROUTE_47":
        return None
    witness = next((cell for cell in cells if len(cell["heights"]) > 1), None)
    if witness is None:
        raise ValueError("Route 47 : surface inférieure HGSS non démontrée")
    low, high = witness["heights"][:2]
    ceiling = (low + high) // 2
    image, _ = renderer.render(header, ceiling)
    image.save(folder / "lower.png")
    display = DisplayMap(header.constant, *image.size, level_count(*image.size), image)
    write_tiles(display, folder / "lower-tiles")
    return {"witness": witness, "ceiling_fx32": ceiling, "pixels_sha256": _digest(image)}


def _write_inventory(folder: Path) -> None:
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    if len(files) > 100_000:
        raise ValueError("Cartes HGSS : plus de 100 000 fichiers produits")
    _json(
        folder / "inventory.json",
        {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
    )
