"""Sprites des formes embarquées à part du sprite de l'espèce : Zarbi (lettres, puis ponctuation des générations
suivantes), Morphéo, Deoxys et formes de Sinnoh déclarées par version dans pokemon_forms.csv.

Chaque forme a quatre variantes, comme les espèces : sprites/<dossier>/[shiny/]{animated,static}/<forme>.webp.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from string import ascii_lowercase

from PIL import Image

from .sources import DATA_DIR, download_all, pokeapi_sprite


@dataclass(frozen=True)
class FormSprites:
    # Numéro de l'espèce ; ses formes sont <numéro>-<forme>.gif dans PokeAPI/sprites.
    species_id: int
    # Dossier des formes dans les assets (sprites/<dossier>/).
    folder: str
    forms: tuple[str, ...]


UNOWN = FormSprites(201, "unown", (*ascii_lowercase, "exclamation", "question"))
_STYLES = ("", "shiny/")


def form_sprites_of(species: set[int]) -> tuple[FormSprites, ...]:
    """Formes à embarquer pour les espèces `species`."""
    groups: dict[tuple[int, str], list[str]] = {}
    with (DATA_DIR / "pokemon_forms.csv").open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            pokemon, folder = int(row["pokemon_id"]), row["sprite_folder"]
            if pokemon not in species or folder == "pokemon":
                continue
            forms = groups.setdefault((pokemon, folder), [])
            if row["sprite_identifier"] not in forms:
                forms.append(row["sprite_identifier"])
    result = [UNOWN] if UNOWN.species_id in species else []
    return tuple(result + [FormSprites(pokemon, folder, tuple(forms)) for (pokemon, folder), forms in groups.items()])


def form_jobs(cache: Path, output: Path, sprites: FormSprites) -> list[tuple[Path, Path]]:
    """Télécharge les animations épinglées et extrait leur première image : (image en cache, destination)."""
    downloads = []
    for style in _STYLES:
        for form in sprites.forms:
            url, path = pokeapi_sprite(
                cache, f"pokemon/versions/generation-v/black-white/animated/{style}{sprites.species_id}-{form}.gif"
            )
            downloads.append((url, path, style, form))
    missing = download_all([(url, path) for url, path, _, _ in downloads])
    if missing:
        raise RuntimeError(f"Sprites des formes de {sprites.folder} introuvables : " + ", ".join(missing))
    jobs = []
    for _, path, style, form in downloads:
        first = path.with_name(f"{path.stem}.first-frame.png")
        if not first.is_file():
            with Image.open(path) as image:
                image.seek(0)
                image.convert("RGBA").save(first, "PNG")
        folder = output / sprites.folder / style
        jobs.extend(((path, folder / "animated" / f"{form}.webp"), (first, folder / "static" / f"{form}.webp")))
    return jobs


def validate_form_sprites(output: Path, sprites: FormSprites) -> None:
    """Chaque forme a ses quatre variantes ; le fixe reproduit les pixels de la première image."""
    for style in _STYLES:
        folder = output / sprites.folder / style
        for form in sprites.forms:
            with (
                Image.open(folder / "animated" / f"{form}.webp") as animated,
                Image.open(folder / "static" / f"{form}.webp") as static,
            ):
                animated.seek(0)
                if (
                    animated.size != static.size
                    or animated.convert("RGBA").tobytes() != static.convert("RGBA").tobytes()
                ):
                    raise RuntimeError(f"Sprite fixe différent de son animation : {sprites.folder}/{style}{form}")
