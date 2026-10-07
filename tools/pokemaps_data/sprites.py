"""Récupère les images embarquées dans l'application.

- Pokémon : un seul style partout (carte, listes, fiches, Pokédex, évolutions), les sprites animés de
  Noir et Blanc (PokeAPI/sprites). Le sprite fixe est la première image du sprite animé : mêmes dessin,
  pose et taille, que l'animation soit activée ou non.
- Icônes d'objets : msikma/pokesprite.

Les images sont embarquées en WebP sans perte (`webp.py`). Arborescence produite dans les assets :
    sprites/pokemon/animated/<pokemon_id>.webp
    sprites/pokemon/static/<pokemon_id>.webp
    sprites/items/<item_identifier>.webp
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from .builder import DatabaseBuilder
from .sources import download, download_all, pokeapi_sprite, pokesprite
from .webp import encode_all

# Icônes pokesprite des CT / CS : une par type d'attaque.
MACHINE_ICON = "items/{kind}/{type}.png"
# Objets sans icône dans pokesprite : icône d'un objet semblable.
ICON_FALLBACKS = {"bike-voucher": "items/key-item/ss-ticket.png"}
# Sprites animés (GIF) de Noir et Blanc : les Pokémon des générations 1 à 5 (n° 1 à 649) seulement.
ANIMATED_SPRITES = "pokemon/versions/generation-v/black-white/animated/{id}.gif"
LAST_ANIMATED_SPECIES = 649


def build_sprites(builder: DatabaseBuilder, cache: Path, output: Path) -> set[str]:
    """Télécharge les images dans le cache, les encode en WebP puis les copie dans `output`.

    Renvoie les identifiants des objets qui ont une icône."""
    missing = sorted(species for species in builder.species if species > LAST_ANIMATED_SPECIES)
    if missing:
        raise RuntimeError(
            f"Pas de sprite animé Noir et Blanc pour les Pokémon n° {missing[0]} à {missing[-1]} : "
            "choisir une autre source de sprites pour ces générations (sprites.py)"
        )
    animated = []  # (url, cache, numéro)
    for species_id in sorted(builder.species):
        url, path = pokeapi_sprite(cache, ANIMATED_SPRITES.format(id=species_id))
        animated.append((url, path, species_id))
    item_paths = _item_icon_paths(builder, cache)
    items = [(*pokesprite(cache, sprite_path), identifier) for identifier, sprite_path in item_paths.items()]

    not_found = download_all([(url, path) for url, path, _ in animated + items])
    if not_found:
        raise RuntimeError("Images introuvables :\n" + "\n".join(not_found))

    jobs: list[tuple[Path, Path]] = []  # (image en cache, destination)
    for _, path, species_id in animated:
        jobs.append((path, output / "pokemon/animated" / f"{species_id}.webp"))
        jobs.append((_first_frame(path), output / "pokemon/static" / f"{species_id}.webp"))
    jobs += [(path, output / "items" / f"{identifier}.webp") for _, path, identifier in items]

    encoded = encode_all([path for path, _ in jobs])
    if output.exists():
        shutil.rmtree(output)
    for path, destination in jobs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(encoded[path], destination)
    return set(item_paths)


def _first_frame(animation: Path) -> Path:
    """Première image d'un sprite animé, enregistrée en PNG à côté de lui dans le cache."""
    target = animation.with_name(f"{animation.stem}.first-frame.png")
    if not target.is_file():
        with Image.open(animation) as image:
            image.seek(0)
            frame = image.convert("RGBA")
        partial = target.with_name(f"{target.name}.part")
        frame.save(partial, "PNG")
        partial.replace(target)
    return target


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
    move_types = {(row[0], row[1]): row[2] for row in builder.moves.move_version_group_table()}
    for vg, item_id, move_id in builder.moves.machine_rows:
        machine_types.setdefault(item_id, move_types[(move_id, vg)])
    types = {type_id: row["identifier"] for type_id, row in builder.type_rows.items()}

    result = {}
    for item_id, identifier, _, _ in builder.items.item_rows:
        if item_id in machine_types:
            kind = "hm" if identifier.startswith("hm") else "tm"
            result[identifier] = MACHINE_ICON.format(kind=kind, type=types[machine_types[item_id]])
        elif f"item_{gen8_index.get(item_id, 0):04d}" in item_map:
            result[identifier] = f"items/{item_map[f'item_{gen8_index[item_id]:04d}']}.png"
        elif identifier in ICON_FALLBACKS:
            result[identifier] = ICON_FALLBACKS[identifier]
    return result
