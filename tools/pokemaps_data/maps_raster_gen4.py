"""Rasterisation entière des triangles DS, avec profondeur, texels et transparence.

Le sol reste à une unité monde par pixel (16 pixels par case). La projection oblique remonte les
points de hauteur h de h × cotangente ; aucune opération flottante ne participe aux pixels.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from .pret_gen4_textures import Rgba, Texture

ONE = 4096
_MAX_SIDE = 2048


@dataclass(frozen=True)
class RasterVertex:
    position: tuple[int, int, int]
    texcoord: tuple[int, int]
    color: tuple[int, int, int]


@dataclass(frozen=True)
class RasterTexture:
    source: Texture
    pixels: tuple[Rgba, ...]

    def sample(self, s: int, t: int) -> Rgba:
        texture = self.source
        x = _wrap(s, texture.width, texture.repeat[0], texture.flip[0])
        y = _wrap(t, texture.height, texture.repeat[1], texture.flip[1])
        return self.pixels[y * texture.width + x]


def _wrap(value: int, size: int, repeat: bool, flip: bool) -> int:
    if not repeat:
        return min(size - 1, max(0, value))
    period, offset = divmod(value, size)
    return size - 1 - offset if flip and period % 2 else offset


@dataclass(frozen=True)
class RasterMaterial:
    texture: RasterTexture | None
    alpha: int
    faces: int

    def __post_init__(self) -> None:
        if not 0 <= self.alpha <= 31 or not 0 <= self.faces <= 3:
            raise ValueError("attributs de polygone DS invalides")


@dataclass(frozen=True)
class _Point:
    x: int
    y: int
    depth: int
    height: int
    vertex: RasterVertex


class RasterCanvas:
    def __init__(
        self, origin: tuple[int, int], size: tuple[int, int], cotangent: int, ceiling: int | None = None
    ) -> None:
        if not all(0 < side <= _MAX_SIDE for side in size) or not 0 <= cotangent <= 16 * ONE:
            raise ValueError(f"cadre ou projection DS invalide : {origin}, {size}, {cotangent}")
        self.origin = origin
        self.size = size
        self.cotangent = cotangent
        self.ceiling = ceiling
        self._colors: list[Rgba] = [(0, 0, 0, 0)] * (size[0] * size[1])
        self._depth: list[int | None] = [None] * len(self._colors)

    def _project(self, vertex: RasterVertex, offset: tuple[int, int], cotangent: int) -> _Point:
        x, height, z = vertex.position
        return _Point(
            x + (offset[0] - self.origin[0]) * ONE,
            z - height * cotangent // ONE + (offset[1] - self.origin[1]) * ONE,
            height + (z + offset[1] * ONE) * cotangent // ONE,
            height,
            vertex,
        )

    def triangle(
        self,
        vertices: tuple[RasterVertex, RasterVertex, RasterVertex],
        material: RasterMaterial,
        offset: tuple[int, int] = (0, 0),
        cotangent: int | None = None,
    ) -> None:
        if material.alpha == 0:
            return
        angle = self.cotangent if cotangent is None else cotangent
        a, b, c = (self._project(vertex, offset, angle) for vertex in vertices)
        area = _edge(a, b, c.x, c.y)
        if area == 0 or not material.faces & (2 if area < 0 else 1):
            return
        if area < 0:
            b, c, area = c, b, -area
        if self.ceiling is not None and min(a.height, b.height, c.height) > self.ceiling:
            return
        left = max(0, min(a.x, b.x, c.x) // ONE)
        right = min(self.size[0] - 1, max(a.x, b.x, c.x) // ONE)
        top = max(0, min(a.y, b.y, c.y) // ONE)
        bottom = min(self.size[1] - 1, max(a.y, b.y, c.y) // ONE)
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                self._pixel(x, y, (a, b, c), area, material)

    def _pixel(
        self, x: int, y: int, points: tuple[_Point, _Point, _Point], area: int, material: RasterMaterial
    ) -> None:
        a, b, c = points
        px, py = x * ONE + ONE // 2, y * ONE + ONE // 2
        w0 = _edge(b, c, px, py)
        if w0 < 0:
            return
        w1 = _edge(c, a, px, py)
        w2 = area - w0 - w1
        if w1 < 0 or w2 < 0:
            return
        # Une arête partagée appartient à un seul triangle, y compris pour les polygones translucides.
        if (
            (w0 == 0 and not _inclusive(b, c))
            or (w1 == 0 and not _inclusive(c, a))
            or (w2 == 0 and not _inclusive(a, b))
        ):
            return
        if self.ceiling is not None and (a.height * w0 + b.height * w1 + c.height * w2) // area > self.ceiling:
            return
        depth = (a.depth * w0 + b.depth * w1 + c.depth * w2) // area
        index = y * self.size[0] + x
        previous = self._depth[index]
        if previous is not None and depth < previous:
            return
        color = _color(points, (w0, w1, w2), area, material)
        if color[3] == 0:
            return
        self._colors[index] = _over(color, self._colors[index])
        if color[3] == 31:
            self._depth[index] = depth

    def image(self) -> Image.Image:
        pixels = bytes((component << 3) | (component >> 2) for pixel in self._colors for component in pixel)
        return Image.frombytes("RGBA", self.size, pixels)


def _edge(a: _Point, b: _Point, x: int, y: int) -> int:
    return (b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)


def _inclusive(a: _Point, b: _Point) -> bool:
    return b.y < a.y or (b.y == a.y and b.x > a.x)


def _color(
    points: tuple[_Point, _Point, _Point], weights: tuple[int, int, int], area: int, material: RasterMaterial
) -> Rgba:
    texel: Rgba = (31, 31, 31, 31)
    a, b, c = (point.vertex for point in points)
    w0, w1, w2 = weights
    if material.texture is not None:
        s = (a.texcoord[0] * w0 + b.texcoord[0] * w1 + c.texcoord[0] * w2) // (area * 16)
        t = (a.texcoord[1] * w0 + b.texcoord[1] * w1 + c.texcoord[1] * w2) // (area * 16)
        texel = material.texture.sample(s, t)
    channels = tuple((a.color[k] * w0 + b.color[k] * w1 + c.color[k] * w2) // area for k in range(3))
    rgb = tuple(((texel[k] + 1) * (channels[k] + 1) - 1) >> 5 for k in range(3))
    return (*rgb, ((texel[3] + 1) * (material.alpha + 1) - 1) >> 5)


def _over(source: Rgba, destination: Rgba) -> Rgba:
    if source[3] == 31:
        return source
    alpha = source[3] * 31 + destination[3] * (31 - source[3])
    if alpha == 0:
        return (0, 0, 0, 0)
    rgb = tuple(
        (source[k] * source[3] * 31 + destination[k] * destination[3] * (31 - source[3])) // alpha for k in range(3)
    )
    return (*rgb, alpha // 31)
