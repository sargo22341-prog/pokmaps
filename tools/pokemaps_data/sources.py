"""Sources de données, figées sur des commits précis pour des builds reproductibles.

- PokéAPI : export CSV du dépôt PokeAPI/pokeapi (mêmes données que l'API https://pokeapi.co).
  On télécharge les CSV une fois au build : l'application n'appelle jamais l'API
  (cf. la politique d'usage équitable : https://pokeapi.co/docs/v2#fairuse).
- PokeAPI/sprites : sprites animés de Noir et Blanc, seul style de sprite des Pokémon.
- msikma/pokesprite : icônes d'objets.
- pret/pokered, pret/pokeyellow : désassemblages des jeux, uniquement pour générer les cartes.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import TracebackType
from typing import Any

POKEAPI_COMMIT = "bc92d3b6029ef1abe9e7ad424c400b338f3c11fe"
POKEAPI_CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/{commit}/data/v2/csv/{name}.csv"

POKEAPI_SPRITES_COMMIT = "bfb75391935310368065096fa08c51e8970bc43e"
POKEAPI_SPRITES_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/{commit}/sprites/{path}"

POKESPRITE_COMMIT = "c5aaa610ff2acdf7fd8e2dccd181bca8be9fcb3e"
POKESPRITE_URL = "https://raw.githubusercontent.com/msikma/pokesprite/{commit}/{path}"

DOWNLOAD_TIMEOUT_SECONDS = 60
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

# Désassemblages pret (https://github.com/pret) : cartes, tilesets, objets et palettes.
PRET_COMMITS = {
    "pokered": "d2704a63c26f9ba046ade877445216b3de0519a4",
    "pokeyellow": "e89ead154b9968aa50eed9328ff2b38b6c194382",
}
PRET_URL = "https://github.com/pret/{repo}.git"

POKEAPI_CSV_FILES = (
    "encounter_condition_value_map",
    "encounter_condition_value_prose",
    "encounter_condition_values",
    "encounter_method_prose",
    "encounter_methods",
    "encounter_slots",
    "encounters",
    "evolution_triggers",
    "evolution_trigger_prose",
    "generation_names",
    "generations",
    "growth_rate_prose",
    "growth_rates",
    "item_categories",
    "item_flavor_text",
    "item_game_indices",
    "item_names",
    "items",
    "location_area_encounter_rates",
    "location_area_prose",
    "location_areas",
    "location_names",
    "locations",
    "machines",
    "move_changelog",
    "move_names",
    "moves",
    "pokedex_prose",
    "pokedex_version_groups",
    "pokedexes",
    "pokemon",
    "pokemon_dex_numbers",
    "pokemon_evolution",
    "pokemon_move_methods",
    "pokemon_move_method_prose",
    "pokemon_moves",
    "pokemon_species",
    "pokemon_species_flavor_text",
    "pokemon_species_names",
    "pokemon_stats",
    "pokemon_stats_past",
    "pokemon_types",
    "pokemon_types_past",
    "region_names",
    "regions",
    "stat_names",
    "stats",
    "type_efficacy",
    "type_efficacy_past",
    "type_names",
    "types",
    "version_groups",
    "version_names",
    "versions",
)


def download(url: str, path: Path) -> bool:
    """Télécharge `url` dans `path` s'il n'est pas déjà en cache. Renvoie False si la ressource n'existe pas."""
    if path.exists():
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"Ressource trop volumineuse ({content_length} octets) : {url}")
            with tmp.open("wb") as output:
                total = 0
                while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError(f"Ressource trop volumineuse (plus de {MAX_DOWNLOAD_BYTES} octets) : {url}")
                    output.write(chunk)
    except urllib.error.HTTPError as error:
        tmp.unlink(missing_ok=True)
        if error.code == 404:
            return False
        raise
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(path)
    return True


def download_all(jobs: list[tuple[str, Path]]) -> list[str]:
    """Télécharge en parallèle ; renvoie les URL introuvables (404)."""
    jobs = list(dict.fromkeys(jobs))  # plusieurs fichiers peuvent partager la même image
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda job: download(*job), jobs))
    return [url for (url, _), ok in zip(jobs, results, strict=True) if not ok]


def fetch_pokeapi_csv(cache: Path) -> Path:
    """Télécharge les CSV PokéAPI nécessaires dans `cache/pokeapi-<commit>`."""
    target = cache / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    jobs = [
        (POKEAPI_CSV_URL.format(commit=POKEAPI_COMMIT, name=name), target / f"{name}.csv") for name in POKEAPI_CSV_FILES
    ]
    missing = download_all(jobs)
    if missing:
        raise RuntimeError(f"CSV PokéAPI introuvables : {missing}")
    return target


def pokeapi_sprite(cache: Path, path: str) -> tuple[str, Path]:
    url = POKEAPI_SPRITES_URL.format(commit=POKEAPI_SPRITES_COMMIT, path=path)
    return url, cache / f"pokeapi-sprites-{POKEAPI_SPRITES_COMMIT[:12]}" / path


def pokesprite(cache: Path, path: str) -> tuple[str, Path]:
    url = POKESPRITE_URL.format(commit=POKESPRITE_COMMIT, path=path)
    return url, cache / f"pokesprite-{POKESPRITE_COMMIT[:12]}" / path


def pret_dir(cache: Path, repo: str) -> Path:
    """Dossier du dépôt pret `repo` dans le cache ; il ne contient la source complète que si `.complete` existe."""
    return cache / f"{repo}-{PRET_COMMITS[repo][:12]}"


def fetch_pret(cache: Path, repo: str) -> Path:
    """Récupère le dépôt pret `repo` au commit figé dans `cache/<repo>-<commit>` (sans l'historique git)."""
    commit = PRET_COMMITS[repo]
    target = pret_dir(cache, repo)
    if (target / ".complete").exists():
        return target
    if target.exists():
        _remove_tree(target)
    target.mkdir(parents=True)

    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(target), *args], check=True, capture_output=True)

    git("init", "-q")
    git("fetch", "-q", "--depth", "1", PRET_URL.format(repo=repo), commit)
    git("checkout", "-q", "FETCH_HEAD")
    _remove_tree(target / ".git")
    (target / ".complete").touch()
    return target


def _remove_tree(path: Path) -> None:
    """Supprime aussi les fichiers en lecture seule créés par Git sous Windows."""

    def retry_removal(
        function: Callable[[str], Any],
        failing_path: str,
        _error: tuple[type[OSError], OSError, TracebackType | None],
    ) -> None:
        os.chmod(failing_path, stat.S_IREAD | stat.S_IWRITE)
        function(failing_path)

    shutil.rmtree(path, onerror=retry_removal)
