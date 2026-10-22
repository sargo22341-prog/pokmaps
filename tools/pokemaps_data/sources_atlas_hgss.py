"""Empreintes des ressources natives du catalogue intégral HGSS."""

import json
from pathlib import Path

from .sources import HGSS_PRET_COMMIT
from .validate_hgss_maps import _file_digest

ATLAS_MANIFEST = Path(__file__).resolve().parents[2] / "docs/generations/cartes-hgss-atlas-sources.json"


def validate_atlas_sources(root: Path) -> dict[str, str]:
    manifest = json.loads(ATLAS_MANIFEST.read_text(encoding="utf-8"))
    if manifest["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("Catalogue HGSS : commit des sources incohérent")
    for relative, digest in (manifest["files"] | manifest.get("contracts", {})).items():
        path = root / relative
        if not path.is_file() or _file_digest(path) != digest:
            raise ValueError(f"{relative} : source du catalogue HGSS absente ou modifiée")
    return manifest["files"]


def atlas_contracts() -> dict[str, str]:
    return json.loads(ATLAS_MANIFEST.read_text(encoding="utf-8")).get("contracts", {})
