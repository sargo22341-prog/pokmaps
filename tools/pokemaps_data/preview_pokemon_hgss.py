"""Aperçu HGSS autonome, validé en staging avant remplacement ; aucun asset Android modifié."""

import hashlib
import json
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from .catalog_pokemon_hgss import pokemon_catalog
from .compare_pokemon_hgss import compare_pokemon
from .pokeapi import PokeApi
from .pokemon_forms_hgss import build_forms, copy_sprites
from .pret_hgss_pokemon import read_hgss_pokemon
from .sources import DATA_DIR, HGSS_PRET_COMMIT, POKEAPI_COMMIT, fetch_pokeapi_csv

_INVENTORY = Path(__file__).resolve().parents[2] / "docs/generations/pokemon-hgss-sources.json"


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_sources(root: Path, api: Path) -> dict:
    inventory = json.loads(_INVENTORY.read_text(encoding="utf-8"))
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if result.stdout.strip() != HGSS_PRET_COMMIT or inventory["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("HGSS Pokémon : commit natif différent de la source épinglée")
    if inventory["pokeapi_commit"] != POKEAPI_COMMIT:
        raise ValueError("HGSS Pokémon : commit PokéAPI différent de la source épinglée")
    for folder, key in ((root, "native"), (api, "pokeapi")):
        for name, expected in inventory[key].items():
            path = folder / name
            if not path.is_file() or path.stat().st_size > 64 * 1024 * 1024:
                raise ValueError(f"HGSS Pokémon : source absente ou trop volumineuse : {path}")
            data = path.read_bytes()
            if path.suffix in {".json", ".h", ".c", ".s", ".txt", ".csv"}:
                data = data.replace(b"\r\n", b"\n")
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"HGSS Pokémon : source modifiée : {path}")
    return inventory


def build_hgss_pokemon(cache: Path, output: Path, assets: Path) -> None:
    started = time.perf_counter()
    root = (cache / "hgss-qualification").resolve()
    target = (output / "hgss-pokemon").resolve()
    protected = (cache.resolve(), assets.resolve(), Path(__file__).resolve().parents[2] / "app/src/main/assets")
    if any(target.is_relative_to(p) or p.is_relative_to(target) for p in protected):
        raise ValueError("L'aperçu Pokémon HGSS doit rester séparé des sources et des assets distribués")
    api_root = fetch_pokeapi_csv(cache)
    sources = validate_sources(root, api_root)
    api = PokeApi(api_root)
    native = read_hgss_pokemon(root)
    rules = json.loads((DATA_DIR / "hgss_pokemon_rules.json").read_text(encoding="utf-8"))
    if rules["versions"] != ["heartgold", "soulsilver"]:
        raise ValueError("HGSS : les règles doivent couvrir les deux cartouches uniquement")
    sources["editorial"] = {
        name: hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()
        for name in ("hgss_pokemon_rules.json", "hgss_pokemon_forms.csv")
    }
    comparison = compare_pokemon(native, api)
    validate_comparison(comparison, rules)
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".hgss-pokemon-", dir=target.parent) as temporary:
        staging = Path(temporary) / "hgss-pokemon"
        staging.mkdir()
        forms = build_forms(native, rules)
        sprites = copy_sprites(assets, root, staging, forms)
        catalog = pokemon_catalog(native, api, rules, forms)
        _json(staging / "pokemon.json", catalog)
        _json(staging / "comparison.json", comparison)
        _json(staging / "sources.json", sources | {"sprites": sprites, "native_format": "HGSS"})
        _json(
            staging / "inventory.json",
            {
                p.relative_to(staging).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(staging.rglob("*"))
                if p.is_file()
            },
        )
        _replace_preview(staging, target, Path(temporary) / "previous")
    size = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
    print(
        f"Aperçu Pokémon HGSS validé : {target} (493 espèces, 2 versions, {size} octets, "
        f"{time.perf_counter() - started:.2f} s)"
    )


def validate_comparison(comparison: dict, rules: dict) -> None:
    if comparison["learnset_differences"] or comparison["stat_differences"]:
        raise ValueError(f"HGSS : différence d'attaques ou de statistiques inexpliquée : {comparison}")
    if comparison["profile_differences"] != rules["comparison_capture_rates"]:
        raise ValueError(f"HGSS : différence de profil inexpliquée : {comparison['profile_differences']}")


def _replace_preview(staging: Path, target: Path, previous: Path) -> None:
    if target.exists():
        target.rename(previous)
    try:
        staging.rename(target)
    except OSError:
        if previous.exists():
            previous.rename(target)
        raise
