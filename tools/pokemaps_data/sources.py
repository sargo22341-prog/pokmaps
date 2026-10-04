"""Sources de données, figées sur des commits précis pour des builds reproductibles."""

from __future__ import annotations

import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GitSource:
    name: str
    url: str
    commit: str


PRET_RED_BLUE = GitSource("pokered", "https://github.com/pret/pokered", "d2704a63c26f9ba046ade877445216b3de0519a4")
PRET_YELLOW = GitSource("pokeyellow", "https://github.com/pret/pokeyellow", "e89ead154b9968aa50eed9328ff2b38b6c194382")

POKEAPI_COMMIT = "bc92d3b6029ef1abe9e7ad424c400b338f3c11fe"
POKEAPI_CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/{commit}/data/v2/csv/{name}.csv"
POKEAPI_CSV_FILES = (
    "items",
    "item_names",
    "moves",
    "move_names",
    "pokemon",
    "pokemon_species_names",
    "pokemon_species_flavor_text",
    "types",
    "type_names",
)


def fetch_git(source: GitSource, cache: Path) -> Path:
    """Récupère `source` au commit demandé dans `cache/<nom>` (sans historique)."""
    target = cache / source.name
    if (target / ".git").exists():
        head = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        if head == source.commit:
            return target
    target.mkdir(parents=True, exist_ok=True)
    git = ["git", "-C", str(target)]
    if not (target / ".git").exists():
        subprocess.run([*git, "init", "--quiet"], check=True)
        subprocess.run([*git, "remote", "add", "origin", source.url], check=True)
    subprocess.run([*git, "fetch", "--quiet", "--depth", "1", "origin", source.commit], check=True)
    subprocess.run([*git, "checkout", "--quiet", "--force", "FETCH_HEAD"], check=True)
    return target


def fetch_pokeapi_csv(cache: Path) -> Path:
    """Télécharge les CSV PokéAPI nécessaires dans `cache/pokeapi-<commit>`."""
    target = cache / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    target.mkdir(parents=True, exist_ok=True)
    for name in POKEAPI_CSV_FILES:
        path = target / f"{name}.csv"
        if path.exists():
            continue
        url = POKEAPI_CSV_URL.format(commit=POKEAPI_COMMIT, name=name)
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return target
