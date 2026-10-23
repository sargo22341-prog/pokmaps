"""Alignement des points d'herbe HGSS sur la texture réellement visible du rendu natif."""

from pathlib import Path

from PIL import Image

# Palette diurne de l'herbe HGSS épinglée ; les arbres, chemins et sols unis ont d'autres couleurs.
_GRASS_COLORS = frozenset({(66, 165, 99), (49, 148, 90), (41, 123, 90), (74, 181, 115), (90, 206, 123), (41, 132, 99)})


def align_grass(path: Path, terrain: dict, const: str) -> dict:
    if not terrain.get("grass"):
        return terrain
    with Image.open(path) as source:
        image = source.convert("RGB")
        if image.width * image.height > 64 * 1024 * 1024:
            raise ValueError(f"{path} : image trop grande pour le placement d'herbe")
        points = {
            (x, y)
            for y in range(8, image.height - 8, 16)
            for x in range(8, image.width - 8, 16)
            if _grass_neighborhood(image, x, y)
        }
        points.update(tuple(p) for p in terrain["grass"] if _grass_neighborhood(image, *p))
    if points:
        return terrain | {"grass": sorted(points)}
    # Les quelques comportements d'herbe dans les grottes ne correspondent pas à de l'herbe dessinée.
    # Leurs rencontres utilisent le sol validé ; le Safari conserve ses habitats rocheux particuliers.
    if terrain.get("floor") and not const.startswith("MAP_SAFARI_ZONE_"):
        return {kind: points for kind, points in terrain.items() if kind != "grass"}
    return terrain


def _grass_neighborhood(image: Image.Image, x: int, y: int) -> bool:
    if x < 4 or y < 4 or x + 4 >= image.width or y + 4 >= image.height:
        return False
    if image.getpixel((x, y)) not in _GRASS_COLORS:
        return False
    return sum(image.getpixel((x + dx, y + dy)) in _GRASS_COLORS for dx in (-4, 0, 4) for dy in (-4, 0, 4)) >= 8
