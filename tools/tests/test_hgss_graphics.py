"""Commandes Nitro rencontrées par Johto et découpage des grands rendus HGSS."""

import struct
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data import maps_render_hgss
from pokemaps_data.maps_geometry_gen4 import ShapeDraw, Transform, shape_draws
from pokemaps_data.maps_raster_gen4 import RasterMaterial, RasterVertex
from pokemaps_data.maps_render_gen4 import _vertex
from pokemaps_data.maps_render_hgss import HgssRenderer
from pokemaps_data.pret_gen4_gx import TRIANGLES, Vertex, primitives
from pokemaps_data.pret_gen4_map_models import LightingPeriod
from pokemaps_data.pret_gen4_nitro import SbcCommand, _inverse_binds, read_nsbmd
from pokemaps_data.pret_gen4_source import ByteReader
from pokemaps_data.pret_hgss_maps import HgssHeader, HgssMapRepo
from tests.test_gen4_nitro import display_list, nsbmd, vertex16

_ONE = 4096
_IDENTITY = (_ONE, 0, 0, 0, _ONE, 0, 0, 0, _ONE)


def test_gx_scale_accumulates_until_matrix_restore() -> None:
    data = display_list(
        (0x1B, (2048, 2048, 2048)),
        (0x40, (TRIANGLES,)),
        vertex16(1, 2, 3),
        (0x1B, (2048, 2048, 2048)),
        vertex16(1, 2, 3),
        (0x14, (3,)),
        vertex16(1, 2, 3),
        (0x41, ()),
    )
    vertices = primitives(data, "Arène d’Irisia")[0].vertices
    assert vertices[0].matrix_scale == (2048, 2048, 2048)
    assert vertices[1].matrix_scale == (1024, 1024, 1024)
    assert vertices[2].matrix_scale == (_ONE, _ONE, _ONE) and vertices[2].matrix == 3


def test_billboard_faces_camera_and_preserves_translation_and_scale() -> None:
    model = read_nsbmd(nsbmd(bytes([1])), "témoin").models[0]
    node = replace(model.nodes[0], translation=(5, 6, 7), scale=(2 * _ONE,) * 3)
    commands = (
        SbcCommand(6, 1, (0, 0, 0, 1)),
        SbcCommand(7, 3, (0, 2, 1)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(1, 0, ()),
    )
    model = replace(model, nodes=(node,), render=commands)
    rotation = (_ONE, 0, 0, 0, 0, -_ONE, 0, _ONE, 0)
    draw = next(shape_draws(model, rotation))
    assert draw.transform.point((0, _ONE, 0)) == (5, 6, 7 - 2 * _ONE)
    assert dict(draw.stack)[2] == draw.transform
    with pytest.raises(ValueError, match="SBC non gérée"):
        list(shape_draws(model))


def test_envelope_inverse_bind_cancels_initial_bone_pose() -> None:
    model = read_nsbmd(nsbmd(bytes([1])), "témoin").models[0]
    root = replace(model.nodes[0], translation=(10, 0, 0))
    child = replace(root, translation=(0, 20, 0))
    commands = (
        SbcCommand(6, 1, (0, 0, 0, 0)),
        SbcCommand(6, 3, (1, 0, 0, 1, 0)),
        SbcCommand(9, 0, (2, 2, 0, 0, 128, 1, 1, 128)),
        SbcCommand(5, 0, (0,)),
        SbcCommand(1, 0, ()),
    )
    model = replace(
        model, nodes=(root, child), render=commands, inverse_binds=((*_IDENTITY, -10, 0, 0), (*_IDENTITY, -10, -20, 0))
    )
    assert next(shape_draws(model)).transform == Transform()
    with pytest.raises(ValueError, match="matrice d'enveloppe absente"):
        list(shape_draws(replace(model, inverse_binds=())))


def test_gx_restore_does_not_apply_sbc_position_scale_twice() -> None:
    model = read_nsbmd(nsbmd(bytes([1])), "Arène de Rosalia").models[0]
    draw = ShapeDraw(0, 0, Transform(), ((0, Transform()),), 64 * _ONE)
    vertex = Vertex((_ONE, 0, 0), (0, 0), (31, 31, 31), None, 0, (64 * _ONE,) * 3)
    lighting = LightingPeriod(0, (), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0))
    result = _vertex(vertex, draw, model, model.materials[0], (0, 0, 0), (_ONE,) * 3, lighting)
    assert result.position == (64 * _ONE, 0, 0)
    original = _vertex(
        replace(vertex, matrix=None, matrix_scale=(_ONE,) * 3),
        draw,
        model,
        model.materials[0],
        (0, 0, 0),
        (_ONE,) * 3,
        lighting,
    )
    assert original.position == result.position


def test_envelope_reader_bounds_the_native_array() -> None:
    data = bytearray(20)
    struct.pack_into("<I", data, 16, 20)
    data.extend(struct.pack("<12i", *_IDENTITY, 1, 2, 3) + bytes(36))
    assert _inverse_binds(ByteReader(bytes(data), "enveloppe"), 0, len(data), 1) == ((*_IDENTITY, 1, 2, 3),)
    with pytest.raises(ValueError, match="hors du modèle"):
        _inverse_binds(ByteReader(bytes(data), "enveloppe"), 0, len(data) - 1, 1)


class _LargeRepo(HgssMapRepo):
    def blocks(self, header: HgssHeader) -> tuple[tuple[int, int, int, int], ...]:
        return ((0, 0, 0, 0), (4, 0, 0, 0))


def test_large_map_renders_triangles_on_both_sides_of_frame_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    renderer = HgssRenderer(_LargeRepo(Path("fixture"), "heartgold"))
    vertices = tuple(
        RasterVertex((x * _ONE, 0, z * _ONE), (0, 0), (31, 0, 0)) for x, z in ((895, 10), (901, 10), (895, 16))
    )
    monkeypatch.setattr(
        renderer, "triangles", lambda header, block, altitude: ((vertices, RasterMaterial(None, 31, 3)),)
    )
    monkeypatch.setattr(maps_render_hgss, "camera_cotangent", lambda root, header: 0)
    image, origin = renderer.render(HgssHeader(0, "MAP_LARGE", 0, 0, 0, ()))
    assert origin == (-128, -256) and image.size == (2816, 1024)
    assert image.getpixel((1023, 266)) == (255, 0, 0, 255)
    assert image.getpixel((1025, 266)) == (255, 0, 0, 255)
