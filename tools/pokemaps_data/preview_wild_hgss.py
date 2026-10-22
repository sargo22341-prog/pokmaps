"""Aperçu indépendant des rencontres HGSS, vérifié avant remplacement atomique."""

import hashlib
import json
import subprocess
import time
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from .catalog_wild_hgss import encounter_catalog
from .compare_wild_hgss import compare_tables
from .encounters_hgss import Configuration, Distribution, Period, Radio, Slot
from .pokeapi import PokeApi
from .pret_gen4_source import read_json
from .pret_hgss_wild import read_trees, read_wild
from .preview_pokemon_hgss import _replace_preview
from .sources import HGSS_PRET_COMMIT, POKEAPI_COMMIT, fetch_pokeapi_csv
from .validate_hgss_maps import _file_digest
from .validate_johto_hgss import check_johto_preview
from .validate_special_hgss import validate_obtainings, validate_special_wild

_MANIFEST = Path(__file__).resolve().parents[2] / "docs/generations/rencontres-hgss-sources.json"


def validate_sources(root: Path, api: Path) -> dict:
    manifest = read_json(_MANIFEST)
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.stdout.strip() != HGSS_PRET_COMMIT or manifest["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("Rencontres HGSS : commit natif incorrect")
    if manifest["pokeapi_commit"] != POKEAPI_COMMIT:
        raise ValueError("Rencontres HGSS : commit PokéAPI incorrect")
    for folder, key in ((root, "native"), (api, "pokeapi")):
        for name, expected in manifest[key].items():
            path = folder / name
            if not path.is_file() or _digest(path) != expected:
                raise ValueError(f"Rencontres HGSS : source absente ou modifiée : {path}")
    return manifest


def _digest(path: Path) -> str:
    if path.suffix in {".csv", ".py"}:
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError(f"HGSS : texte trop volumineux : {path}")
        return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return _file_digest(path)


def _json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_comparison(report: dict) -> None:
    """Accepte les poids Éclate-Roc prouvés et les tables PokéAPI du quai sans banque native."""
    for row in report["differences"]:
        if row["category"] != "probabilites" or row["method"] != "rock-smash":
            raise ValueError(f"HGSS : écart PokéAPI inexpliqué : {row}")
        old = {tuple(s[:3]): s[3] for s in row["pokeapi"]}
        new = {tuple(s[:3]): s[3] for s in row["engine"]}
        if old.keys() != new.keys() or sorted(old.values()) != [10, 90] or sorted(new.values()) != [20, 80]:
            raise ValueError(f"HGSS : écart Éclate-Roc non reconnu : {row}")
        if any(new[key] != {10: 20, 90: 80}[value] for key, value in old.items()):
            raise ValueError(f"HGSS : inversion des emplacements Éclate-Roc : {row}")
    for row in report.get("source_only", []):
        if (
            row["area"] != 349
            or row["category"] != "table_absente_moteur"
            or row["engine"]
            or row["method"] not in ("surf", "old-rod", "good-rod", "super-rod")
        ):
            raise ValueError(f"HGSS : table PokéAPI sans équivalent natif inexpliquée : {row}")


def build_hgss_encounters(cache: Path, output: Path, assets: Path) -> None:
    started = time.perf_counter()
    root = (cache / "hgss-qualification").resolve()
    target = (output / "hgss-encounters").resolve()
    protected = (
        cache.resolve(),
        assets.resolve(),
        Path(__file__).resolve().parents[2] / "app/src/main/assets",
        (output / "hgss-maps").resolve(),
    )
    if any(target.is_relative_to(p) or p.is_relative_to(target) for p in protected):
        raise ValueError("L'aperçu des rencontres HGSS doit rester séparé des sources, cartes et assets distribués")
    api_root = fetch_pokeapi_csv(cache)
    sources = validate_sources(root, api_root)
    check_johto_preview(output / "hgss-maps")
    maps_digest = _digest(output / "hgss-maps/inventory.json")
    api = PokeApi(api_root)
    tables, headers = read_wild(root)
    trees = read_trees(root)
    catalog = encounter_catalog(root, tables, trees, headers, api)
    report = compare_tables(tables, api)
    validate_comparison(report)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".hgss-encounters-", dir=target.parent) as temporary:
        staging = Path(temporary) / "hgss-encounters"
        staging.mkdir()
        _write_preview(staging, catalog, report, sources, maps_digest)
        check_encounters_preview(staging, output / "hgss-maps")
        _replace_preview(staging, target, Path(temporary) / "previous")
    print(
        f"Rencontres HGSS validées : {len(tables)} distributions, {len(trees)} tables d'arbres, "
        f"{report['equal']} comparaisons identiques, {len(report['differences'])} écarts classés ; "
        f"{len(report['source_only'])} tables PokéAPI sans équivalent natif ; "
        f"{time.perf_counter() - started:.2f} s — {target}"
    )


def _write_preview(staging: Path, catalog: dict, report: dict, sources: dict, maps_digest: str) -> None:
    _json(staging / "encounters.json", catalog)
    _json(staging / "comparison.json", report)
    _json(staging / "sources.json", sources | {"maps_inventory_sha256": maps_digest, "recipe": _recipe()})
    _json(
        staging / "summary.json",
        {
            "distributions": len(catalog["distributions"]),
            "headbutt": len(catalog["headbutt"]),
            "equal": report["equal"],
            "differences": dict(Counter(r["category"] for r in report["differences"])),
            "source_only": len(report.get("source_only", [])),
        },
    )
    _json(staging / "inventory.json", {p.name: _digest(p) for p in sorted(staging.iterdir())})


def check_encounters_preview(folder: Path, maps: Path | None = None) -> None:
    inventory = read_json(folder / "inventory.json")
    if set(inventory) != {"encounters.json", "comparison.json", "sources.json", "summary.json"}:
        raise ValueError("HGSS : inventaire des rencontres incomplet")
    for name, expected in inventory.items():
        if _digest(folder / name) != expected:
            raise ValueError(f"HGSS : aperçu des rencontres modifié : {name}")
    sources = read_json(folder / "sources.json")
    manifest = read_json(_MANIFEST)
    if any(sources.get(key) != value for key, value in manifest.items()) or sources.get("recipe") != _recipe():
        raise ValueError("HGSS : sources ou recette de l'aperçu des rencontres périmées")
    prerequisite = (maps if maps is not None else folder.parent / "hgss-maps") / "inventory.json"
    if not prerequisite.is_file() or _digest(prerequisite) != sources["maps_inventory_sha256"]:
        raise ValueError("HGSS : prérequis cartographique absent ou périmé pour les rencontres")
    path = folder / "encounters.json"
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("HGSS : catalogue des rencontres trop volumineux")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    if catalog["commit"] != HGSS_PRET_COMMIT or catalog["versions"] != ["heartgold", "soulsilver"]:
        raise ValueError("HGSS : provenance des rencontres incorrecte")
    for table in catalog["distributions"] + catalog["headbutt"]:
        _validate_distribution(table)
    if catalog.get("scope") == "4A-4D":
        validate_special_wild(catalog["special_wild"])
        validate_obtainings(catalog["obtainings"])
    validate_comparison(read_json(folder / "comparison.json"))


def _validate_distribution(table: dict) -> None:
    raw = table["configuration"]
    config = Configuration(Period(raw["period"]), Radio(raw["radio"]), raw["swarm"], raw["national"], raw["weekday"])
    Distribution(
        table["version"],
        table["bank"],
        table["method"],
        config,
        table["rate"],
        tuple(Slot(**slot) for slot in table["slots"]),
    )


def _recipe() -> dict[str, str]:
    names = (
        "special_wild_hgss.py",
        "obtainings_hgss.py",
        "validate_special_hgss.py",
        "encounters_hgss.py",
        "pret_hgss_wild.py",
        "compare_wild_hgss.py",
        "catalog_wild_hgss.py",
        "preview_wild_hgss.py",
    )
    folder = Path(__file__).resolve().parent
    return {name: _digest(folder / name) for name in names} | {
        "hgss_maps.csv": _digest(folder.parent / "data/hgss_maps.csv")
    }
