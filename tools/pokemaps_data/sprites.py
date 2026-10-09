"""Récupère les images embarquées dans l'application.

- Pokémon : un seul style partout (carte, listes, fiches, Pokédex, évolutions), les sprites animés de
  Noir et Blanc (PokeAPI/sprites), normaux et chromatiques. Le sprite fixe est la première image du sprite
  animé : mêmes dessin, pose et taille, que l'animation soit activée ou non.
- Formes embarquées à part (Zarbi, Morphéo, Deoxys) : mêmes sprites et variantes (`form_sprites.py`).
- Icônes d'objets : msikma/pokesprite, trouvées par le numéro de l'objet dans les jeux de 8e génération, sinon par
  son identifiant parmi les icônes que pokesprite ne relie à aucun numéro (data/item-unlinked.json).

Les images sont embarquées en WebP sans perte (`webp.py`). Arborescence produite dans les assets :
    sprites/pokemon/animated/<pokemon_id>.webp
    sprites/pokemon/static/<pokemon_id>.webp
    sprites/pokemon/shiny/animated/<pokemon_id>.webp
    sprites/pokemon/shiny/static/<pokemon_id>.webp
    sprites/items/<item_identifier>.webp
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from .builder import DatabaseBuilder
from .form_sprites import form_jobs, form_sprites_of, validate_form_sprites
from .sources import download, download_all, pokeapi_sprite, pokesprite
from .webp import encode_all

# Icônes pokesprite des CT / CS : une par type d'attaque. pokesprite n'en a pas pour le type « ??? » (Malédiction,
# CT03 d'Or et d'Argent) : elle prend l'icône d'une CT de type Normal.
MACHINE_ICON = "items/{kind}/{type}.png"
MACHINE_TYPE_FALLBACKS = {"unknown": "normal"}
# Sprites animés (GIF) de Noir et Blanc : les Pokémon des générations 1 à 5 (n° 1 à 649) seulement.
ANIMATED_SPRITES = "pokemon/versions/generation-v/black-white/animated/{id}.gif"
SHINY_SPRITES = "pokemon/versions/generation-v/black-white/animated/shiny/{id}.gif"
# Dossier de chaque style dans les assets (sprites/pokemon/<dossier>/animated et /static).
POKEMON_STYLES = ((ANIMATED_SPRITES, "pokemon"), (SHINY_SPRITES, "pokemon/shiny"))
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
    animated = []  # (url, cache, dossier des assets, numéro)
    for sprite_path, folder in POKEMON_STYLES:
        for species_id in sorted(builder.species):
            url, path = pokeapi_sprite(cache, sprite_path.format(id=species_id))
            animated.append((url, path, folder, species_id))
    item_paths = _item_icon_paths(builder, cache)
    items = [(*pokesprite(cache, sprite_path), identifier) for identifier, sprite_path in item_paths.items()]

    not_found = download_all([(url, path) for url, path, *_ in animated + items])
    if not_found:
        raise RuntimeError("Images introuvables :\n" + "\n".join(not_found))

    jobs: list[tuple[Path, Path]] = []  # (image en cache, destination)
    for _, path, folder, species_id in animated:
        jobs.append((path, output / folder / "animated" / f"{species_id}.webp"))
        jobs.append((_first_frame(path), output / folder / "static" / f"{species_id}.webp"))
    jobs += [(path, output / "items" / f"{identifier}.webp") for _, path, identifier in items]

    forms = form_sprites_of(set(builder.species))
    for sprites in forms:
        jobs += form_jobs(cache, output, sprites)
    encoded = encode_all([path for path, _ in jobs])
    if output.exists():
        shutil.rmtree(output)
    for path, destination in jobs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(encoded[path], destination)
    for sprites in forms:
        validate_form_sprites(output, sprites)
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
    item_map: dict[str, str] = _pokesprite_data(cache, "data/item-map.json")
    by_identifier = icons_by_identifier(item_map, _pokesprite_data(cache, "data/item-unlinked.json"))
    # pokesprite indexe les objets par leur numéro dans les jeux de 8e génération.
    gen8_index = {
        int(row["item_id"]): int(row["game_index"])
        for row in builder.api.table("item_game_indices")
        if row["generation_id"] == "8"
    }
    machine_types = builder.moves.machine_types()
    types = {row[0]: row[1] for row in builder.type_table()}

    result = {}
    for item_id, identifier, _, _ in builder.items.item_rows:
        if item_id in machine_types:
            kind = "hm" if identifier.startswith("hm") else "tm"
            move_type = types[machine_types[item_id]]
            result[identifier] = MACHINE_ICON.format(kind=kind, type=MACHINE_TYPE_FALLBACKS.get(move_type, move_type))
        elif f"item_{gen8_index.get(item_id, 0):04d}" in item_map:
            result[identifier] = f"items/{item_map[f'item_{gen8_index[item_id]:04d}']}.png"
        elif identifier in by_identifier:
            result[identifier] = by_identifier[identifier]
    return result


def icons_by_identifier(item_map: dict[str, str], unlinked: dict[str, object]) -> dict[str, str]:
    """Nom de fichier d'une icône pokesprite (« mail/orange-mail » -> « orange-mail ») -> chemin de l'icône, pour les
    icônes reliées à un numéro puis pour les autres. Un nom porté par deux icônes différentes n'est pas retenu."""
    candidates: dict[str, set[str]] = {}
    for icon in (*item_map.values(), *unlinked):
        candidates.setdefault(icon.rsplit("/", 1)[-1], set()).add(f"items/{icon}.png")
    return {name: paths.pop() for name, paths in candidates.items() if len(paths) == 1}


def _pokesprite_data(cache: Path, path: str) -> dict:
    url, local = pokesprite(cache, path)
    download(url, local)
    return json.loads(local.read_text("utf-8"))
