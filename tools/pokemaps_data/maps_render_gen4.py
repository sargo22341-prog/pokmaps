"""Rendu borné des blocs DS depuis les lecteurs pret, sans GPU ni dépendance supplémentaire.

Les textures de base sont conservées ; les animations ne sont pas avancées. Un format de rendu
non pris en charge arrête l'export avec le modèle concerné, jamais avec une image incomplète.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image

from .maps_bindings_gen4 import bind_palettes, read_palette_bindings
from .maps_dynamic_gen4 import DynamicProps, prop_rotation
from .maps_geometry_gen4 import ShapeDraw, Transform, Vector, shape_draws
from .maps_raster_gen4 import RasterCanvas, RasterMaterial, RasterTexture, RasterVertex
from .maps_render import DisplayMap, level_count, write_tiles
from .pret_gen4 import Gen4PretRepo
from .pret_gen4_gx import Vertex, primitives, triangles
from .pret_gen4_map_models import LightingPeriod
from .pret_gen4_nitro import FX_ONE, NitroFile, NitroMaterial, NitroModel, read_nsbmd
from .pret_gen4_prop_animations import PropAnimations
from .pret_gen4_textures import NitroTextures, Palette, Texture, decode

_UNIT_SCALE = (FX_ONE, FX_ONE, FX_ONE)
_IDENTITY_TRANSFORM = Transform()
_BLOCK_PX = 512

RasterTriangle = tuple[tuple[RasterVertex, RasterVertex, RasterVertex], RasterMaterial]


@dataclass(frozen=True)
class BlockRender:
    block: int
    area: int
    cotangent: int
    altitude: int = 0
    ceiling: int | None = None
    margin: int = 128

    def __post_init__(self) -> None:
        if not 0 <= self.margin <= 256 or not 0 <= self.altitude <= 255:
            raise ValueError(f"marge ou altitude DS invalide : {self}")


class Gen4Renderer:
    def __init__(self, repo: Gen4PretRepo) -> None:
        self.repo = repo
        self._terrain_files: dict[int, NitroFile] = {}
        self._prop_files: dict[int, NitroFile] = {}
        self._terrain_textures: dict[int, NitroTextures] = {}
        self._props_textures: dict[int, NitroTextures] = {}
        self._prepared: dict[BlockRender, tuple[RasterTriangle, ...]] = {}
        self._bindings = read_palette_bindings()
        self._animations = PropAnimations(repo)
        self._dynamic = DynamicProps(repo)

    def write_block(self, request: BlockRender, output: Path) -> int:
        image = self.render_block(request)
        display = DisplayMap(str(request.block), image.width, image.height, level_count(*image.size), image)
        return write_tiles(display, output)

    def render_block(self, request: BlockRender) -> Image.Image:
        """Image avec débord au nord/sud : son origine est (-marge, -marge), en pixels du bloc."""
        size = _BLOCK_PX + request.margin * 2
        canvas = RasterCanvas((-request.margin, -request.margin), (size, size), request.cotangent, request.ceiling)
        self.draw_block(canvas, request)
        return canvas.image()

    def draw_block(self, canvas: RasterCanvas, request: BlockRender, offset: tuple[int, int] = (0, 0)) -> None:
        prepared = self.prepare_block(request)
        for translucent in (False, True):
            for vertices, material in prepared:
                if (material.alpha < 31) == translucent:
                    canvas.triangle(vertices, material, offset)

    def prepare_block(self, request: BlockRender) -> tuple[RasterTriangle, ...]:
        if request in self._prepared:
            return self._prepared[request]
        if len(self._prepared) >= 16:
            del self._prepared[next(iter(self._prepared))]
        area = self.repo.areas[request.area]
        light = next(period for period in self.repo.lighting[area.lighting] if period.end_time >= 25200)
        block = self.repo.land_block(request.block)
        origin = (256 * FX_ONE, request.altitude * 8 * FX_ONE, 256 * FX_ONE)
        terrain = self._terrain(request.block)
        terrain_textures = self._map_textures(area.texture_set)
        prop_textures = self._prop_textures(area.prop_set)
        result = list(self._file(terrain, (terrain_textures, prop_textures), origin, _UNIT_SCALE, light))
        for prop in block.props:
            position = tuple(a + b for a, b in zip(origin, prop.position, strict=True))
            if request.ceiling is not None and position[1] > request.ceiling:
                continue
            # AreaDataManager_GetMapPropModelFile substitue dmybox00 si le modèle n'est pas chargé dans la zone.
            model = prop.model if prop.model in self.repo.prop_sets[area.prop_set] else 0
            result.extend(self._file(self._prop(model), (prop_textures, terrain_textures), position, prop.scale, light))
        for prop in self._dynamic.by_block.get((request.block, request.area), ()):
            position = tuple(value * FX_ONE for value in prop.position)
            position = (position[0], position[1] + origin[1], position[2])
            if request.ceiling is not None and position[1] > request.ceiling:
                continue
            result.extend(
                self._file(
                    self._prop(prop.model),
                    (prop_textures, terrain_textures),
                    position,
                    _UNIT_SCALE,
                    light,
                    prop_rotation(prop.rotation),
                )
            )
        self._prepared[request] = tuple(result)
        return self._prepared[request]

    def _terrain(self, index: int) -> NitroFile:
        if index not in self._terrain_files:
            self._terrain_files[index] = read_nsbmd(
                self.repo.land_block(index).model, f"{self.repo.variant} bloc {index}"
            )
        return self._terrain_files[index]

    def _prop(self, index: int) -> NitroFile:
        if index not in self._prop_files:
            self._prop_files[index] = self._animations.first_frame(index, self.repo.prop_model(index))
        return self._prop_files[index]

    def _map_textures(self, index: int) -> NitroTextures:
        if index not in self._terrain_textures:
            self._terrain_textures[index] = bind_palettes(
                self.repo.map_textures(index), self.repo.variant, index, self._bindings
            )
        return self._terrain_textures[index]

    def _prop_textures(self, index: int) -> NitroTextures:
        if index not in self._props_textures:
            self._props_textures[index] = self.repo.prop_textures(index)
        return self._props_textures[index]

    def _file(
        self,
        file: NitroFile,
        textures: tuple[NitroTextures, ...],
        origin: Vector,
        scale: Vector,
        lighting: LightingPeriod,
        placement: Transform = _IDENTITY_TRANSFORM,
    ) -> Iterator[RasterTriangle]:
        for model in file.models:
            for draw in shape_draws(model):
                material = model.materials[draw.material]
                raster_material = _material(material, file.textures, textures)
                if raster_material.alpha == 0:
                    continue
                for primitive in primitives(model.shapes[draw.shape].display_list, model.name):
                    for triangle in triangles(primitive):
                        vertices = tuple(
                            _vertex(vertex, draw, model, material, origin, scale, lighting, placement)
                            for vertex in triangle
                        )
                        yield vertices, raster_material


@lru_cache(maxsize=256)
def _texture(source: Texture, palette: Palette | None) -> RasterTexture:
    return RasterTexture(source, decode(source, palette))


def _material(
    material: NitroMaterial, embedded: NitroTextures | None, external: tuple[NitroTextures, ...]
) -> RasterMaterial:
    texture = None
    if material.texture is not None:
        sets = ((embedded,) if embedded is not None else ()) + external
        source = next((value.textures[material.texture] for value in sets if material.texture in value.textures), None)
        palette = next((value.palettes[material.palette] for value in sets if material.palette in value.palettes), None)
        if source is None:
            raise ValueError(f"matériau {material.name} : texture absente : {material.texture}")
        texture = _texture(source, palette)
    return RasterMaterial(texture, material.polygon_attributes >> 16 & 31, material.polygon_attributes >> 6 & 3)


def _vertex(
    vertex: Vertex,
    draw: ShapeDraw,
    model: NitroModel,
    material: NitroMaterial,
    origin: Vector,
    scale: Vector,
    lighting: LightingPeriod,
    placement: Transform = _IDENTITY_TRANSFORM,
) -> RasterVertex:
    stack = dict(draw.stack)
    if vertex.matrix is not None and vertex.matrix not in stack:
        raise ValueError(f"{model.name} : matrice GX {vertex.matrix} non initialisée")
    transform = draw.transform if vertex.matrix is None else stack[vertex.matrix]
    point = tuple(value * draw.position_scale // FX_ONE for value in vertex.position)
    point = transform.point(point)
    point = placement.point(tuple(point[k] * scale[k] // FX_ONE for k in range(3)))
    position = tuple(point[k] + origin[k] for k in range(3))
    color = vertex.color if vertex.color is not None else _shade(vertex, transform.then(placement), material, lighting)
    uv = _texcoord(vertex.texcoord, material)
    return RasterVertex(position, uv, color)


def _texcoord(uv: tuple[int, int], material: NitroMaterial) -> tuple[int, int]:
    sine, cosine = material.texture_rotation
    width, height = material.original_size
    u, v = uv[0] - width * 8, uv[1] - height * 8
    rotated = ((u * cosine + v * sine) // FX_ONE + width * 8, (-u * sine + v * cosine) // FX_ONE + height * 8)
    return tuple(
        rotated[k] * material.texture_scale[k] // FX_ONE
        + material.texture_translation[k] * material.original_size[k] * 16 // FX_ONE
        for k in range(2)
    )


def _shade(vertex: Vertex, transform: Transform, material: NitroMaterial, period: LightingPeriod) -> Vector:
    if vertex.normal is None:
        return (31, 31, 31)
    normal = Transform(transform.rotation).point(tuple(value * 8 for value in vertex.normal))
    # AreaLightTemplate_ApplyToModelAttributes remplace les réflexions de tous les matériaux du terrain.
    diffuse, ambient, emission = period.diffuse, period.ambient, period.emission
    colors = list(emission)
    for index, light in enumerate(period.lights):
        if not light.enabled or not material.polygon_attributes & (1 << index):
            continue
        intensity = max(0, -sum(a * b for a, b in zip(normal, light.direction, strict=True)) // FX_ONE)
        for channel in range(3):
            colors[channel] += ambient[channel] * light.color[channel] // 32
            colors[channel] += diffuse[channel] * light.color[channel] * intensity // (32 * FX_ONE)
    return tuple(min(31, value) for value in colors)
