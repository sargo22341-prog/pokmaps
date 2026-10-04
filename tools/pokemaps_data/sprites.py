"""Récupère les images embarquées dans l'application.

- Icônes de boîte des Pokémon et icônes d'objets : msikma/pokesprite.
- Sprites des jeux (ex. Rouge/Bleu, Jaune) et sprites animés (Noir/Blanc) : PokeAPI/sprites.

Arborescence produite dans les assets :
    sprites/pokemon/icon/<pokemon_id>.png
    sprites/pokemon/<version_group>/<pokemon_id>.png
    sprites/pokemon/animated/<pokemon_id>.gif
    sprites/items/<item_identifier>.png
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .builder import DatabaseBuilder
from .sources import download, download_all, pokeapi_sprite, pokesprite

# Icônes pokesprite des CT / CS : une par type d'attaque.
MACHINE_ICON = "items/{kind}/{type}.png"
# Objets sans icône dans pokesprite : icône d'un objet semblable.
ICON_FALLBACKS = {"bike-voucher": "items/key-item/ss-ticket.png"}
# Sprites animés (GIF) de Noir et Blanc, les seuls animés pour toute la 1re génération (affichage en option).
ANIMATED_SPRITES = "pokemon/versions/generation-v/black-white/animated/{id}.gif"


def build_sprites(builder: DatabaseBuilder, cache: Path, output: Path) -> set[str]:
    """Télécharge les images dans le cache puis les copie dans `output`.

    Renvoie les identifiants des objets qui ont une icône."""
    jobs: list[tuple[str, Path, Path]] = []  # (url, cache, destination)

    # Icônes des Pokémon (pokesprite, noms de fichier = slug anglais).
    url, path = pokesprite(cache, "data/pokemon.json")
    download(url, path)
    slugs = {int(number): entry["slug"]["eng"] for number, entry in json.loads(path.read_text("utf-8")).items()}
    for species_id in builder.species:
        url, path = pokesprite(cache, f"pokemon-gen8/regular/{slugs[species_id]}.png")
        jobs.append((url, path, output / "pokemon/icon" / f"{species_id}.png"))

    # Sprites des jeux configurés.
    vg_identifiers = {int(row["id"]): row["identifier"] for row in builder.vg_rows}
    for game, vg in zip(builder.games, builder.vg_ids, strict=True):
        for species_id in sorted(builder.pokemon_by_version_group[vg]):
            url, path = pokeapi_sprite(cache, f"pokemon/{game.sprite_folder}/{species_id}.png")
            jobs.append((url, path, output / "pokemon" / vg_identifiers[vg] / f"{species_id}.png"))

    # Sprites animés.
    for species_id in builder.species:
        url, path = pokeapi_sprite(cache, ANIMATED_SPRITES.format(id=species_id))
        jobs.append((url, path, output / "pokemon/animated" / f"{species_id}.gif"))

    # Icônes des objets.
    item_paths = _item_icon_paths(builder, cache)
    for identifier, sprite_path in item_paths.items():
        url, path = pokesprite(cache, sprite_path)
        jobs.append((url, path, output / "items" / f"{identifier}.png"))

    missing = download_all([(url, path) for url, path, _ in jobs])
    if missing:
        raise RuntimeError("Images introuvables :\n" + "\n".join(missing))

    if output.exists():
        shutil.rmtree(output)
    for _, path, destination in jobs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    return set(item_paths)


def _item_icon_paths(builder: DatabaseBuilder, cache: Path) -> dict[str, str]:
    """Identifiant d'objet -> chemin de son icône dans pokesprite."""
    url, path = pokesprite(cache, "data/item-map.json")
    download(url, path)
    item_map: dict[str, str] = json.loads(path.read_text("utf-8"))

    # pokesprite indexe les objets par leur numéro dans les jeux de 8e génération.
    gen8_index = {
        int(row["item_id"]): int(row["game_index"])
        for row in builder.api.table("item_game_indices")
        if row["generation_id"] == "8"
    }
    machine_types: dict[int, int] = {}
    move_types = {(row[0], row[1]): row[2] for row in builder.move_version_group_table()}
    for vg, item_id, move_id in builder.machine_rows:
        machine_types.setdefault(item_id, move_types[(move_id, vg)])
    types = {type_id: row["identifier"] for type_id, row in builder.type_rows.items()}

    result = {}
    for item_id, identifier, _, _ in builder.item_rows:
        if item_id in machine_types:
            kind = "hm" if identifier.startswith("hm") else "tm"
            result[identifier] = MACHINE_ICON.format(kind=kind, type=types[machine_types[item_id]])
        elif f"item_{gen8_index.get(item_id, 0):04d}" in item_map:
            result[identifier] = f"items/{item_map[f'item_{gen8_index[item_id]:04d}']}.png"
        elif identifier in ICON_FALLBACKS:
            result[identifier] = ICON_FALLBACKS[identifier]
    return result
