"""Contrôles hors sources des inventaires et références des catalogues préparatoires HGSS."""

import hashlib
import json
from pathlib import Path

from PIL import Image

from .preview_johto_hgss import _MANIFEST, _catalog_recipe, _recipe, validate_johto_output
from .sources import HGSS_PRET_COMMIT
from .sources_atlas_hgss import ATLAS_MANIFEST
from .validate_hgss_maps import _file_digest


def check_johto_preview(root: Path) -> dict:
    inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()} - {"inventory.json"}
    if not inventory or len(inventory) > 100_000 or set(inventory) != files:
        raise ValueError(f"{root} : inventaire HGSS incomplet")
    for relative, expected in inventory.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"{relative} : empreinte HGSS modifiée")
    catalog = _check_catalog(root / "johto", _MANIFEST)
    _check_catalog(root / "atlas", ATLAS_MANIFEST)
    return catalog


def _check_catalog(folder: Path, manifest: Path) -> dict:
    catalog = json.loads((folder / "catalog.json").read_text(encoding="utf-8"))
    if catalog["commit"] != HGSS_PRET_COMMIT or catalog["geometry_versions"] != ["heartgold", "soulsilver"]:
        raise ValueError(f"{folder} : provenance HGSS incohérente")
    if catalog["sources"] != json.loads(manifest.read_text(encoding="utf-8"))["files"]:
        raise ValueError(f"{folder} : qualification des sources HGSS périmée")
    contracts = json.loads(manifest.read_text(encoding="utf-8")).get("contracts", {})
    if catalog.get("contract_sources", {}) != contracts:
        raise ValueError(f"{folder} : contrats des variantes HGSS périmés")
    if catalog["recipe"] != _recipe(catalog["sources"]):
        raise ValueError(f"{folder} : recette de rendu HGSS périmée")
    if catalog.get("catalog_recipe") != _catalog_recipe():
        raise ValueError(f"{folder} : recette du catalogue HGSS périmée")
    editorial = Path(__file__).resolve().parents[1] / "data"
    for name, expected in catalog["editorial_sources"].items():
        if _file_digest(editorial / name) != expected:
            raise ValueError(f"{name} : catalogue éditorial HGSS périmé")
    validate_johto_output(folder, catalog)
    if catalog.get("scope") == "atlas":
        _check_safari(catalog)
    for record in catalog["maps"]:
        _check_render(folder, record)
        layers = record.get("layers", [])
        nonvisual = record.get("nonvisual_slices", [])
        ceilings = {layer["ceiling_fx32"] for layer in layers + nonvisual}
        if len(ceilings) != len(layers) + len(nonvisual) or len(ceilings) > 256:
            raise ValueError(f"{record['const']} : coupes de terrain dupliquées ou trop nombreuses")
        for layer in layers:
            if layer["header"] != record["header"] or not layer["witnesses"] or layer["layers"]:
                raise ValueError(f"{record['const']} : coupe sans témoin ou avec références incohérentes")
            _check_render(folder, layer)
        for candidate in nonvisual:
            if candidate["kind"] != "below_static_geometry" or not candidate["witnesses"] or not candidate["reason"]:
                raise ValueError(f"{record['const']} : surface non visuelle sans justification")
    for plan in catalog["plans"]:
        for level in range(plan["level_count"]):
            if not any((folder / "plans" / plan["id"] / str(level)).glob("*.webp")):
                raise ValueError(f"{plan['id']} : niveau de tuiles absent : {level}")
        if plan["layout"] == "native":
            validate_world_tiles(folder / "plans" / plan["id"], plan)
    return catalog


def validate_world_tiles(folder: Path, plan: dict) -> None:
    level = plan["level_count"] - 1
    width, height = plan["size"]
    for path in (folder / str(level)).glob("*.webp"):
        row, column = map(int, path.stem.split("_"))
        with Image.open(path) as tile:
            if tile.size != (256, 256) or not (0 <= column * 256 < width and 0 <= row * 256 < height):
                raise ValueError(f"{path} : tuile de raccord HGSS hors cadre ou de taille incorrecte")


def _check_render(folder: Path, record: dict) -> None:
    path = folder / record["image"]
    with Image.open(path) as image:
        if image.size != tuple(record["size"]) or image.width * image.height > 32_000_000:
            raise ValueError(f"{path} : dimensions HGSS incohérentes")
        if hashlib.sha256(image.tobytes()).hexdigest() != record["pixels_sha256"]:
            raise ValueError(f"{path} : pixels HGSS différents du catalogue")
    for level in range(record["level_count"]):
        if not any((path.parent / "tiles" / str(level)).glob("*.webp")):
            raise ValueError(f"{path} : niveau de tuiles absent : {level}")


def _check_safari(catalog: dict) -> None:
    safari = catalog["safari"]
    maps = {r["header"] for r in catalog["maps"]}
    templates = [dict(area=i, header=343 + i, block=652 + i) for i in range(12)]
    slots = [dict(column=x + 1, row=z + 1) for z in range(2) for x in range(3)]
    sets = safari["initial_sets"]
    if (
        safari["runtime_header"] != 357
        or safari["matrix"] != 212
        or safari["templates"] != templates
        or safari["slots"] != slots
        or not {357, *(t["header"] for t in templates)} <= maps
        or len(sets) != 10
        or any(len(s) != 6 or len(set(s)) != 6 or not set(s) <= set(range(12)) for s in sets)
    ):
        raise ValueError("Safari HGSS : gabarits, emplacements ou configurations incohérents")
