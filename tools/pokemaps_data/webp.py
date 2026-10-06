"""Encode les images embarquées en WebP sans perte : plus léger que PNG et GIF, pixels identiques.

Mesuré sur les assets de Rouge/Bleu et Jaune : −30 % pour les icônes et sprites fixes (PNG), −8 % (environ
400 Ko) pour les sprites animés (GIF). L'encodage le plus compact (`method=6`) prend plusieurs minutes pour les
sprites animés : chaque image encodée est gardée en cache à côté de sa source téléchargée, et l'encodage se fait
sur plusieurs fils (Pillow libère le GIL pendant l'encodage).

Chaque image encodée est relue et comparée à sa source (images, durées, pixels visibles) : la génération
s'arrête si une seule diffère. Ce contrôle n'est pas théorique : libwebp recadre chaque image d'une animation
sur sa partie visible et omet l'alpha si toutes ces parties sont opaques, ce qui rendrait le fond noir.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageChops, ImageSequence

# Réglages de l'encodeur. Les changer impose de changer ENCODING, qui nomme les fichiers en cache.
WEBP_LOSSLESS = {"lossless": True, "quality": 100, "method": 6}
ENCODING = "lossless-m6"
TRANSPARENT = (0, 0, 0, 0)
# Durée maximale de l'encodage de toutes les images (quelques minutes sans cache, sur un seul cœur).
ENCODE_TIMEOUT_SECONDS = 30 * 60

# Image et sa durée d'affichage en millisecondes (0 pour une image fixe).
_Frame = tuple[Image.Image, int]


def cached_webp(source: Path) -> Path:
    """Fichier WebP gardé en cache pour l'image `source`."""
    return source.with_name(f"{source.name}.{ENCODING}.webp")


def encode_all(sources: list[Path]) -> dict[Path, Path]:
    """Encode les images (une fois chacune) en WebP, en réutilisant le cache. Renvoie source -> WebP."""
    unique = list(dict.fromkeys(sources))
    todo = [source for source in unique if not cached_webp(source).is_file()]
    pool = ThreadPoolExecutor(max_workers=os.cpu_count())
    try:
        for _ in pool.map(_encode, todo, timeout=ENCODE_TIMEOUT_SECONDS):
            pass
    finally:
        # Délai dépassé ou image refusée : les images pas encore commencées sont abandonnées.
        pool.shutdown(cancel_futures=True)
    return {source: cached_webp(source) for source in unique}


def _encode(source: Path) -> None:
    with Image.open(source) as image:
        frames = _frames(image, source)
        loop = image.info.get("loop", 0)
    target = cached_webp(source)
    # Écriture en deux temps : une génération interrompue ou refusée ne laisse rien dans le cache.
    partial = target.with_name(f"{target.name}.part")
    try:
        _save(frames, loop, partial)
        with Image.open(partial) as encoded:
            if _timeline(_frames(encoded, partial)) != _timeline(frames):
                raise ValueError(f"WebP différent de son image source : {source}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def _save(frames: list[_Frame], loop: int, path: Path) -> None:
    first, _ = frames[0]
    if len(frames) == 1:
        first.save(path, "WEBP", **WEBP_LOSSLESS)
        return
    rest = [frame for frame, _ in frames[1:]]
    durations = [duration for _, duration in frames]
    # Fond transparent : sinon Pillow écrit la couleur de fond du GIF, opaque, que des lecteurs appliquent.
    first.save(
        path,
        "WEBP",
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=loop,
        background=TRANSPARENT,
        **WEBP_LOSSLESS,
    )


def _frames(image: Image.Image, path: Path) -> list[_Frame]:
    """Images RGBA (déjà composées) et durées ; une image fixe a une durée de 0."""
    if not getattr(image, "is_animated", False):
        return [(image.convert("RGBA"), 0)]
    frames = []
    for frame in ImageSequence.Iterator(image):
        rgba = frame.convert("RGBA")  # charge l'image : sa durée n'est connue qu'ensuite (WebP)
        duration = frame.info.get("duration")
        if not duration:
            raise ValueError(f"Image animée sans durée d'affichage : {path}")
        frames.append((rgba, int(duration)))
    return frames


def _timeline(frames: list[_Frame]) -> list[tuple[bytes, int]]:
    """Ce que l'on voit, image après image : pixels visibles et durée.

    Les images identiques qui se suivent sont fusionnées (l'encodeur WebP le fait), et la couleur des pixels
    transparents est ignorée (l'encodeur sans perte peut la changer, elle ne se voit pas)."""
    timeline: list[tuple[bytes, int]] = []
    for image, duration in frames:
        pixels = _visible(image).tobytes()
        if timeline and timeline[-1][0] == pixels:
            timeline[-1] = (pixels, timeline[-1][1] + duration)
        else:
            timeline.append((pixels, duration))
    return timeline


def _visible(image: Image.Image) -> Image.Image:
    """Image dont les pixels entièrement transparents sont mis à zéro."""
    opaque = image.getchannel("A").point(lambda alpha: 255 if alpha else 0)
    return ImageChops.multiply(image, Image.merge("RGBA", [opaque] * 4))
