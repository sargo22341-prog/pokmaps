"""Sprites de toutes les formes de Zarbi, y compris la ponctuation des générations suivantes."""

from pathlib import Path
from string import ascii_lowercase

from PIL import Image

from .sources import download_all, pokeapi_sprite

FORMS = (*ascii_lowercase, "exclamation", "question")


def unown_jobs(cache: Path, output: Path) -> list[tuple[Path, Path]]:
    """Télécharge les animations épinglées et extrait leur première image."""
    downloads = []
    for shiny in (False, True):
        style = "shiny/" if shiny else ""
        for form in FORMS:
            url, path = pokeapi_sprite(
                cache, f"pokemon/versions/generation-v/black-white/animated/{style}201-{form}.gif"
            )
            downloads.append((url, path, style, form))
    missing = download_all([(url, path) for url, path, _, _ in downloads])
    if missing:
        raise RuntimeError("Sprites de Zarbi introuvables : " + ", ".join(missing))
    jobs = []
    for _, path, style, form in downloads:
        first = path.with_name(f"{path.stem}.first-frame.png")
        if not first.is_file():
            with Image.open(path) as image:
                image.seek(0)
                image.convert("RGBA").save(first, "PNG")
        folder = output / "unown" / style
        jobs.extend(((path, folder / "animated" / f"{form}.webp"), (first, folder / "static" / f"{form}.webp")))
    return jobs


def validate_unown_sprites(output: Path) -> None:
    """Chaque forme a ses quatre variantes ; le fixe reproduit les pixels de la première image."""
    for style in ("", "shiny"):
        for form in FORMS:
            folder = output / "unown" / style
            with (
                Image.open(folder / "animated" / f"{form}.webp") as animated,
                Image.open(folder / "static" / f"{form}.webp") as static,
            ):
                animated.seek(0)
                if (
                    animated.size != static.size
                    or animated.convert("RGBA").tobytes() != static.convert("RGBA").tobytes()
                ):
                    raise RuntimeError(f"Sprite fixe de Zarbi différent de son animation : {style}/{form}")
