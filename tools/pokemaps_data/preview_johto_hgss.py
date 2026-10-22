"""Aperçu complet des cartes ordinaires de Johto, sans activer les remakes dans Android."""

import hashlib
import json
import multiprocessing
import shutil
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from PIL import Image

from .catalog_maps_hgss import (
    matrix_neighbors,
    passage_catalog,
    passage_surface,
    read_catalog,
    validate_catalog_geometry,
)
from .maps_plans_hgss import write_plan
from .maps_render import DisplayMap, level_count, write_tiles
from .maps_render_hgss import HgssRenderer, camera_cotangent
from .pret_hgss_maps import HgssMapRepo
from .sources import HGSS_PRET_COMMIT
from .validate_hgss_maps import _file_digest

_MANIFEST = Path(__file__).resolve().parents[2] / "docs/generations/cartes-hgss-johto-sources.json"


def _json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_johto_sources(root: Path) -> dict[str, str]:
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    if manifest["commit"] != HGSS_PRET_COMMIT:
        raise ValueError(f"{_MANIFEST} : commit HGSS incohérent")
    for relative, expected in manifest["files"].items():
        if not (root / relative).is_file() or _file_digest(root / relative) != expected:
            raise ValueError(f"{relative} : source Johto HGSS absente ou modifiée")
    return manifest["files"]


def _editorial_sources() -> dict[str, str]:
    return {
        name: _file_digest(Path(__file__).resolve().parents[1] / "data" / name)
        for name in ("hgss_maps.csv", "hgss_map_textures.csv", "hgss_warp_heights.csv")
    }


def build_johto(root: Path, output: Path, cache: Path, workers: int = 4) -> dict:
    sources = validate_johto_sources(root)
    repo = HgssMapRepo(root, "heartgold")
    entries = read_catalog(repo)
    editorial = _editorial_sources()
    validate_catalog_geometry(repo, entries)
    passages = passage_catalog(repo, entries)
    other = HgssMapRepo(root, "soulsilver")
    if repo.headers != other.headers or read_catalog(other) != entries or passage_catalog(other, entries) != passages:
        raise ValueError("Johto : catalogues ou passages différents entre les deux cartouches")
    folder = output / "johto"
    (folder / "maps").mkdir(parents=True)
    key = _recipe(sources)
    renderer = HgssRenderer(repo)
    maps = _render_maps(root, [asdict(e) for e in entries if e.scope == "johto"], folder, cache / key, workers)
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in maps:
        groups[record["plan"]].append(record)
    plans = [write_plan(folder, records, folder / "plans" / name) for name, records in sorted(groups.items())]
    _project_passages(renderer, maps, plans, passages)
    catalog = {
        "commit": HGSS_PRET_COMMIT,
        "maps": maps,
        "plans": plans,
        "passages": passages,
        "matrix_neighbors": matrix_neighbors(repo, entries),
        "inventory": [asdict(entry) for entry in entries],
        "sources": sources,
        "geometry_versions": ["heartgold", "soulsilver"],
        "recipe": key,
        "editorial_sources": editorial,
    }
    if editorial != _editorial_sources():
        raise ValueError("Johto : sources éditoriales modifiées pendant la génération")
    validate_johto_output(folder, catalog)
    _json(folder / "catalog.json", catalog)
    print(f"Johto : {len(maps)} lieux, {len(plans)} plans, {len(passages)} passages, deux versions", flush=True)
    return catalog


def _render_maps(root: Path, entries: list[dict], folder: Path, cache: Path, workers: int) -> list[dict]:
    if not 1 <= workers <= 8:
        raise ValueError("HGSS : le nombre de processus doit être compris entre 1 et 8")
    if workers == 1:
        renderer = HgssRenderer(HgssMapRepo(root, "heartgold"))
        return [_render(renderer, entry, folder, cache) for entry in entries]
    records = []
    with multiprocessing.get_context("spawn").Pool(processes=workers) as pool:
        for start in range(0, len(entries), workers):
            batch = entries[start : start + workers]
            pending = [pool.apply_async(_render_one, (root, entry, folder, cache)) for entry in batch]
            for entry, future in zip(batch, pending, strict=True):
                try:
                    records.append(future.get(timeout=300))
                except multiprocessing.TimeoutError as error:
                    raise ValueError(f"{entry['const']} : rendu HGSS au-delà de 300 secondes") from error
    return records


def _render_one(root: Path, entry: dict, folder: Path, cache: Path) -> dict:
    return _render(HgssRenderer(HgssMapRepo(root, "heartgold")), entry, folder, cache)


def _recipe(sources: dict[str, str]) -> str:
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True).encode())
    module = Path(__file__).resolve().parent
    paths = sorted(module.glob("*gen4*.py"))
    paths.extend(module / name for name in ("maps_render_hgss.py", "pret_hgss_maps.py", "pret_hgss_binary.py"))
    paths.append(module.parent / "data/hgss_map_textures.csv")
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    digest.update(Image.__version__.encode())
    return digest.hexdigest()


def _render(renderer: HgssRenderer, entry: dict, folder: Path, cache: Path) -> dict:
    header = renderer.repo.headers[entry["header"]]
    cache.mkdir(parents=True, exist_ok=True)
    image_path, record_path = cache / f"{header.index}.png", cache / f"{header.index}.json"
    if image_path.is_file() and record_path.is_file():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != record["image_sha256"]:
            raise ValueError(f"{image_path} : cache de rendu HGSS modifié")
    else:
        image, origin = renderer.render(header, complete=True)
        if image.getbbox() is None:
            raise ValueError(f"{header.constant} : rendu HGSS entièrement vide")
        image.save(image_path)
        record = {
            "origin_pixels": origin,
            "size": image.size,
            "pixels_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
            "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
        }
        _json(record_path, record)
    destination = folder / "maps" / str(header.index)
    destination.mkdir()
    shutil.copyfile(image_path, destination / "map.png")
    with Image.open(image_path) as image:
        count = level_count(*image.size)
        write_tiles(DisplayMap(header.constant, *image.size, count, image), destination / "tiles")
    _json(
        destination / "native.json",
        {
            "header": asdict(header),
            "blocks": renderer.repo.blocks(header),
            "events": asdict(renderer.repo.events(header)),
        },
    )
    print(f"  Johto {header.index} : {header.constant}", flush=True)
    return {**entry, **record, "image": f"maps/{header.index}/map.png", "level_count": count}


def _project_passages(renderer: HgssRenderer, maps: list[dict], plans: list[dict], passages: list[dict]) -> None:
    lookup = {record["header"]: record for record in maps}
    offsets = {part["header"]: part["offset"] for plan in plans for part in plan["parts"]}
    for passage in passages:
        surface = passage_surface(renderer.repo, passage["source"], passage["index"])
        passage["source_surface"] = surface
        passage["source_plan"] = lookup[passage["source"]]["plan"]
        passage["source_pixel"] = _pixel(
            renderer, lookup[passage["source"]], offsets[passage["source"]], passage, surface["height_fx32"]
        )
        if passage["kind"] == "fixed":
            destination = passage["destination"]
            surface = passage_surface(renderer.repo, destination, passage["anchor"])
            passage["target_surface"] = surface
            passage["target_plan"] = lookup[destination]["plan"]
            passage["target_pixel"] = _pixel(
                renderer, lookup[destination], offsets[destination], passage["target"], surface["height_fx32"]
            )


def _pixel(renderer: HgssRenderer, record: dict, offset: tuple[int, int], warp: dict, height: int) -> tuple[int, int]:
    from .pret_gen4_land import FX_ONE

    cotangent = camera_cotangent(renderer.repo.root, renderer.repo.headers[record["header"]])
    return (
        warp["x"] * 16 + 8 - record["origin_pixels"][0] + offset[0],
        warp["z"] * 16 + 8 - height * cotangent // FX_ONE // FX_ONE - record["origin_pixels"][1] + offset[1],
    )


def validate_johto_output(folder: Path, catalog: dict) -> None:
    maps = {record["header"]: record for record in catalog["maps"]}
    plans = {plan["id"]: plan for plan in catalog["plans"]}
    expected = {entry["header"] for entry in catalog["inventory"] if entry["scope"] == "johto"}
    if len(maps) != len(catalog["maps"]) or set(maps) != expected or len(plans) != len(catalog["plans"]):
        raise ValueError("Johto : lieu ou plan absent ou dupliqué")
    members = [part["header"] for plan in plans.values() for part in plan["parts"]]
    if len(members) != len(maps) or set(members) != set(maps):
        raise ValueError("Johto : membre de plan absent ou dupliqué")
    if any(maps[part["header"]]["plan"] != plan["id"] for plan in plans.values() for part in plan["parts"]):
        raise ValueError("Johto : affectation de plan incohérente")
    for record in maps.values():
        if record["plan"] not in plans or not (folder / record["image"]).is_file():
            raise ValueError(f"{record['const']} : image ou plan absent")
    offsets = {part["header"]: part["offset"] for plan in plans.values() for part in plan["parts"]}
    for passage in catalog["passages"]:
        for side in ("source", "target"):
            if side == "target" and passage["kind"] != "fixed":
                continue
            plan = plans[passage[f"{side}_plan"]]
            header = passage["source"] if side == "source" else passage["destination"]
            pixel = passage[f"{side}_pixel"]
            local = tuple(pixel[k] - offsets[header][k] for k in (0, 1))
            if any(not 0 <= value < size for value, size in zip(local, maps[header]["size"], strict=True)):
                raise ValueError(f"Johto : passage hors de l'image native : {passage}")
            if any(not 0 <= value < size for value, size in zip(passage[f"{side}_pixel"], plan["size"], strict=True)):
                raise ValueError(f"Johto : passage hors du plan : {passage}")
