"""Sources de données, figées sur des commits précis pour des builds reproductibles.

- PokéAPI : export CSV du dépôt PokeAPI/pokeapi (mêmes données que l'API https://pokeapi.co).
  On télécharge les CSV une fois au build : l'application n'appelle jamais l'API
  (cf. la politique d'usage équitable : https://pokeapi.co/docs/v2#fairuse).
- PokeAPI/sprites : sprites des jeux (ex. Rouge/Bleu, Jaune).
- msikma/pokesprite : icônes de boîte des Pokémon et icônes d'objets.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

POKEAPI_COMMIT = "bc92d3b6029ef1abe9e7ad424c400b338f3c11fe"
POKEAPI_CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/{commit}/data/v2/csv/{name}.csv"

POKEAPI_SPRITES_COMMIT = "bfb75391935310368065096fa08c51e8970bc43e"
POKEAPI_SPRITES_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/{commit}/sprites/{path}"

POKESPRITE_COMMIT = "c5aaa610ff2acdf7fd8e2dccd181bca8be9fcb3e"
POKESPRITE_URL = "https://raw.githubusercontent.com/msikma/pokesprite/{commit}/{path}"

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
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return False
        raise
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
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
