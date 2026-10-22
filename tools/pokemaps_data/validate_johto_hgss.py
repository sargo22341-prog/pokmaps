"""Contrôles hors sources de l'inventaire et des références du catalogue préparatoire Johto."""

import hashlib
import json
from pathlib import Path

from .preview_johto_hgss import _MANIFEST, _recipe, validate_johto_output
from .sources import HGSS_PRET_COMMIT
from .validate_hgss_maps import _file_digest


def check_johto_preview(root: Path) -> dict:
    inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()} - {"inventory.json"}
    if not inventory or len(inventory) > 100_000 or set(inventory) != files:
        raise ValueError(f"{root} : inventaire HGSS incomplet")
    for relative, expected in inventory.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"{relative} : empreinte HGSS modifiée")
    folder = root / "johto"
    catalog = json.loads((folder / "catalog.json").read_text(encoding="utf-8"))
    if catalog["commit"] != HGSS_PRET_COMMIT or catalog["geometry_versions"] != ["heartgold", "soulsilver"]:
        raise ValueError(f"{folder} : provenance HGSS incohérente")
    if catalog["sources"] != json.loads(_MANIFEST.read_text(encoding="utf-8"))["files"]:
        raise ValueError(f"{folder} : qualification des sources HGSS périmée")
    if catalog["recipe"] != _recipe(catalog["sources"]):
        raise ValueError(f"{folder} : recette de rendu HGSS périmée")
    editorial = Path(__file__).resolve().parents[1] / "data"
    for name, expected in catalog["editorial_sources"].items():
        if _file_digest(editorial / name) != expected:
            raise ValueError(f"{name} : catalogue éditorial HGSS périmé")
    validate_johto_output(folder, catalog)
    for plan in catalog["plans"]:
        for level in range(plan["level_count"]):
            if not any((folder / "plans" / plan["id"] / str(level)).glob("*.webp")):
                raise ValueError(f"{plan['id']} : niveau de tuiles absent : {level}")
    return catalog
