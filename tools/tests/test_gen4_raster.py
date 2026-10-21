"""Pixels DS vérifiés sur des triangles synthétiques, sans source extérieure."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from pokemaps_data.maps_geometry_gen4 import Transform, node_transform, shape_draws
from pokemaps_data.maps_raster_gen4 import RasterCanvas, RasterMaterial, RasterTexture, RasterVertex, _color
from pokemaps_data.pret_gen4_gx import TRIANGLES, primitives
from pokemaps_data.pret_gen4_nitro import NitroNode, SbcCommand, read_nsbmd
from pokemaps_data.pret_gen4_textures import PALETTE_16, Texture

from .test_gen4_nitro import display_list, nsbmd, vertex16

ONE = 4096
WHITE = (31, 31, 31)
RED = (31, 0, 0)
BLUE = (0, 0, 31)


def _triangle(height: int, color: tuple[int, int, int]) -> tuple[RasterVertex, RasterVertex, RasterVertex]:
    return tuple(RasterVertex((x * ONE, height * ONE, z * ONE), (0, 0), color) for x, z in ((0, 0), (4, 0), (0, 4)))


def test_normal_replaces_previous_color_and_matrix_starts_unset() -> None:
    data = display_list(
        (0x40, (TRIANGLES,)),
        (0x20, (31,)),
        vertex16(0, 0, 0),
        (0x21, (511 << 10,)),
        vertex16(1, 0, 0),
        (0x20, (31 << 10,)),
        vertex16(0, 0, 1),
        (0x41, ()),
    )
    [primitive] = primitives(data, "triangle")
    a, b, c = primitive.vertices
    assert a.color == RED and a.matrix is None
    assert b.color is None and b.normal == (0, 511, 0)
    assert c.color == BLUE


def test_depth_is_independent_of_opaque_submission_order() -> None:
    pixels = []
    for heights in ((0, 1), (1, 0)):
        canvas = RasterCanvas((0, 0), (4, 4), 0)
        for height in heights:
            canvas.triangle(_triangle(height, RED if height else BLUE), RasterMaterial(None, 31, 3))
        pixels.append(canvas.image().tobytes())
        assert canvas.image().getpixel((0, 0)) == (255, 0, 0, 255)
        assert canvas.image().getpixel((3, 3)) == (0, 0, 0, 0)
    assert pixels[0] == pixels[1]


def test_culling_and_height_ceiling() -> None:
    canvas = RasterCanvas((0, 0), (4, 4), 0, ceiling=ONE)
    canvas.triangle(_triangle(2, RED), RasterMaterial(None, 31, 3))
    canvas.triangle(_triangle(0, RED), RasterMaterial(None, 31, 2))
    assert canvas.image().getbbox() is None
    canvas.triangle(_triangle(1, BLUE), RasterMaterial(None, 31, 1))
    assert canvas.image().getpixel((0, 0)) == (0, 0, 255, 255)


def test_oblique_projection_preserves_ground_and_shifts_raised_vertices() -> None:
    canvas = RasterCanvas((0, -4), (4, 8), ONE)
    canvas.triangle(_triangle(2, RED), RasterMaterial(None, 31, 3))
    assert canvas.image().getpixel((0, 2)) == (255, 0, 0, 255)
    assert canvas.image().getpixel((0, 0)) == (0, 0, 0, 0)


def test_shared_translucent_diagonal_is_blended_once() -> None:
    canvas = RasterCanvas((0, 0), (4, 4), 0)
    vertices = tuple(RasterVertex((x * ONE, 0, z * ONE), (0, 0), RED) for x, z in ((0, 0), (4, 0), (4, 4), (0, 4)))
    canvas.triangle((vertices[0], vertices[1], vertices[2]), RasterMaterial(None, 15, 3))
    canvas.triangle((vertices[0], vertices[2], vertices[3]), RasterMaterial(None, 15, 3))
    assert set(canvas.image().get_flattened_data()) == {(255, 0, 0, 123)}


def test_texture_repeat_flip_clamp_and_transparent_texel() -> None:
    source = Texture("motif", 2, 1, PALETTE_16, True, (True, False), (True, False), bytes(1))
    texture = RasterTexture(source, ((31, 0, 0, 31), (0, 0, 0, 0)))
    assert [texture.sample(x, 0) for x in (-1, 0, 1, 2, 3, 4)] == [
        (31, 0, 0, 31),
        (31, 0, 0, 31),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (31, 0, 0, 31),
        (31, 0, 0, 31),
    ]
    canvas = RasterCanvas((0, 0), (4, 4), 0)
    vertices = tuple(replace(v, texcoord=(16, 0)) for v in _triangle(0, WHITE))
    canvas.triangle(vertices, RasterMaterial(texture, 31, 3))
    assert canvas.image().getbbox() is None


def test_transform_composes_scale_rotation_and_parent_translation() -> None:
    node = NitroNode("enfant", (ONE, 0, 0), (0, 0, ONE, 0, ONE, 0, -ONE, 0, 0), (2 * ONE, ONE, ONE))
    transform = node_transform(node).then(Transform(translation=(0, ONE, 0)))
    assert transform.point((ONE, 0, 0)) == (ONE, ONE, 2 * ONE)


def test_sbc_stack_restores_parent_and_rejects_missing_matrix() -> None:
    [model] = read_nsbmd(nsbmd(bytes([0x06, 0, 0xFF, 0, 0x04, 0, 0x05, 0, 0x01])), "modèle").models
    root = replace(model.nodes[0], translation=(ONE, 0, 0))
    child = replace(root, translation=(0, 2 * ONE, 0))
    commands = (
        SbcCommand(6, 1, (0, 0, 0, 0)),
        SbcCommand(6, 3, (1, 0, 0, 1, 0)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(3, 0, (0,)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(1, 0, ()),
    )
    draws = list(shape_draws(replace(model, nodes=(root, child), render=commands)))
    assert draws[0].transform.point((0, 0, 0)) == (ONE, 2 * ONE, 0)
    assert draws[1].transform.point((0, 0, 0)) == (ONE, 0, 0)
    with pytest.raises(ValueError, match="matrice 2 non initialisée"):
        list(shape_draws(replace(model, render=(SbcCommand(3, 0, (2,)),))))


@pytest.mark.parametrize("size,cotangent", [((0, 4), 0), ((4096, 1), 0), ((1, 1), -1)])
def test_canvas_bounds_are_validated(size: tuple[int, int], cotangent: int) -> None:
    with pytest.raises(ValueError, match="cadre ou projection"):
        RasterCanvas((0, 0), size, cotangent)


@pytest.mark.parametrize("colors", [(WHITE, WHITE, WHITE), (RED, BLUE, WHITE), ((3, 7, 11),) * 3])
def test_color_shortcut_preserves_integer_interpolation(colors: tuple[tuple[int, int, int], ...]) -> None:
    vertices = tuple(replace(vertex, color=color) for vertex, color in zip(_triangle(0, RED), colors, strict=True))
    points = tuple(SimpleNamespace(vertex=vertex) for vertex in vertices)
    for alpha in (0, 15, 31):
        for w0 in range(6):
            for w1 in range(6 - w0):
                weights = (w0, w1, 5 - w0 - w1)
                expected = tuple(
                    sum(color[k] * w for color, w in zip(colors, weights, strict=True)) // 5 for k in range(3)
                )
                assert _color(points, weights, 5, RasterMaterial(None, alpha, 3)) == (*expected, alpha)
