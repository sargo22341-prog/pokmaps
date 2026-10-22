"""Aperçu de placement HGSS : terrain natif, retouches et couverture explicite."""

import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .placement_hgss import coverage, placement_catalog, read_placement_json
from .preview_pokemon_hgss import _replace_preview
from .preview_wild_hgss import check_encounters_preview, validate_sources
from .sources import HGSS_PRET_COMMIT, POKEAPI_COMMIT
from .sources_atlas_hgss import validate_atlas_sources
from .validate_johto_hgss import check_johto_preview

DATA = Path(__file__).resolve().parents[1] / "data"
CONTRACT = DATA.parents[1] / "docs/generations/placements-hgss-sources.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def validate_placement_sources(root: Path) -> dict:
    contract = read_placement_json(CONTRACT)
    if contract["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("HGSS : contrat des terrains d'un autre commit")
    for name, expected in contract["files"].items():
        if digest(root / name) != expected:
            raise ValueError(f"HGSS : source de placement modifiée : {name}")
    return contract


def exceptions(path: Path = DATA / "hgss_spot_exclusions.csv") -> dict[tuple[int, str], str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["header", "kind", "reason"]:
            raise ValueError(f"{path} : colonnes d'exclusion invalides")
        result = {}
        for row in reader:
            key = int(row["header"]), row["kind"]
            if key in result or not row["reason"].strip():
                raise ValueError(f"{path} : exclusion absente ou répétée : {key}")
            result[key] = row["reason"]
    return result


def validate_coverage(rows: list[dict], reasons: dict[tuple[int, str], str]) -> list[dict]:
    used = set()
    result = []
    for row in rows:
        key = row["header"], row["kind"]
        reason = ""
        if not row["points"]:
            if key not in reasons:
                raise ValueError(f"HGSS : lieu sans couverture ni explication : {key}")
            used.add(key)
            reason = reasons[key]
        result.append(row | dict(reason=reason))
    if used != set(reasons):
        raise ValueError(f"HGSS : exclusions de placement inutilisées : {set(reasons) - used}")
    return result


def build_placement(cache: Path, output: Path) -> None:
    root = cache / "hgss-qualification"
    maps = output / "hgss-maps"
    wild = output / "hgss-encounters"
    check_johto_preview(maps)
    check_encounters_preview(wild, maps)
    validate_sources(root, cache / f"pokeapi-{POKEAPI_COMMIT[:12]}")
    native_sources = validate_placement_sources(root)
    validate_atlas_sources(root)
    catalog = placement_catalog(root, maps, read_placement_json(wild / "encounters.json"))
    rows = validate_coverage(coverage(catalog, DATA / "map_spots.csv"), exceptions())
    sources = {
        path.relative_to(output).as_posix(): digest(path) for path in (maps / "inventory.json", wild / "inventory.json")
    }
    recipe = {
        p.name: digest(p)
        for p in (
            Path(__file__),
            Path(__file__).with_name("placement_hgss.py"),
            Path(__file__).with_name("terrain_hgss.py"),
            Path(__file__).with_name("visibility_hgss.py"),
        )
    }
    payload = dict(
        commit=HGSS_PRET_COMMIT,
        native_sources=native_sources,
        sources=sources,
        recipe=recipe,
        spots_sha256=digest(DATA / "map_spots.csv"),
        exclusions_sha256=digest(DATA / "hgss_spot_exclusions.csv"),
        catalog=catalog,
        coverage=rows,
    )
    target = output / "hgss-placement"
    with TemporaryDirectory(prefix=".hgss-placement-", dir=output) as temporary:
        staging = Path(temporary) / "staging"
        staging.mkdir()
        path = staging / "placement.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (staging / "inventory.json").write_text(
            json.dumps({"placement.json": digest(path)}, indent=2) + "\n", encoding="utf-8"
        )
        _replace_preview(staging, target, Path(temporary) / "previous")
    print(
        f"HGSS : {len(catalog['maps'])} lieux, {len(rows)} terrains, "
        f"{sum(r['points'] for r in rows)} points, {sum(not r['points'] for r in rows)} exclusions expliquées"
    )


def check_placement(folder: Path, validate_spots: bool = True) -> dict:
    inventory = read_placement_json(folder / "inventory.json")
    if set(inventory) != {"placement.json"} or digest(folder / "placement.json") != inventory["placement.json"]:
        raise ValueError("HGSS : aperçu de placement modifié")
    data = read_placement_json(folder / "placement.json")
    for name, expected in data["sources"].items():
        if digest(folder.parent / name) != expected:
            raise ValueError(f"HGSS : prérequis de placement périmé : {name}")
    for name, expected in data["recipe"].items():
        if digest(Path(__file__).with_name(name)) != expected:
            raise ValueError(f"HGSS : recette de placement périmée : {name}")
    if data["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("HGSS : provenance du placement incorrecte")
    if data["native_sources"] != read_placement_json(CONTRACT):
        raise ValueError("HGSS : contrat des terrains périmé")
    rows = (
        validate_coverage(coverage(data["catalog"], DATA / "map_spots.csv"), exceptions())
        if validate_spots
        else data["coverage"]
    )
    return data | dict(coverage=rows)
