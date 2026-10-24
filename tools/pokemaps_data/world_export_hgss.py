"""Réexport des seuls pixels régionaux HGSS, avec coordonnées strictement inchangées."""

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from .asset_manifest import write_manifest
from .plans_application_hgss import application_catalog, native_map_types
from .sources import PREVIEW_DIR
from .validate_johto_hgss import check_johto_preview
from .validate_maps_gen4 import write_inventory


def export_worlds(cache: Path, assets: Path) -> None:
    preview = PREVIEW_DIR / "hgss-maps"
    check_johto_preview(preview)
    source = preview / "atlas"
    catalog = json.loads((source / "catalog.json").read_text(encoding="utf-8"))
    updated = application_catalog(catalog, native_map_types(cache / "hgss-qualification"))
    updated = json.loads(json.dumps(updated))
    output = assets / "maps/heartgold-soulsilver"
    destination = output / "catalog.json"
    distributed = json.loads(destination.read_text(encoding="utf-8"))
    previous = distributed["source_catalog"]
    for key in set(previous) | set(updated):
        if key != "catalog_recipe" and previous.get(key) != updated.get(key):
            raise ValueError(f"HGSS : {key} modifié ; une génération complète est nécessaire")
    replacements = {"johto-exterieurs": "johto", "kanto-exterieurs": "kanto"}
    with TemporaryDirectory(prefix="hgss-worlds-", dir=output.parent) as temporary:
        staging = Path(temporary)
        for plan, name in replacements.items():
            shutil.copytree(source / "plans" / plan, staging / name)
        _replace_worlds(output, staging, tuple(replacements.values()))
    distributed["source_catalog"] = updated
    destination.write_text(json.dumps(distributed, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    write_inventory(output)
    write_manifest(assets)
    print("HGSS : Johto et Kanto réexportés, coordonnées et autres données inchangées", flush=True)


def _replace_worlds(output: Path, staging: Path, names: tuple[str, ...]) -> None:
    replaced = []
    try:
        for name in names:
            (output / name).rename(staging / f"previous-{name}")
            replaced.append(name)
            (staging / name).rename(output / name)
    except OSError:
        for name in reversed(replaced):
            if (output / name).exists():
                shutil.rmtree(output / name)
            (staging / f"previous-{name}").rename(output / name)
        raise
