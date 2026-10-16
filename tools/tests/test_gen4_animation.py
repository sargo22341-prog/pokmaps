"""Première image des textures animées et bornes des archives Nitro."""

import struct

import pytest

from pokemaps_data.pret_gen4_animation import animation_first_frame, narc_members
from pokemaps_data.pret_gen4_nitro import read_nsbmd

from .test_gen4_nitro import g3d_dictionary, nitro_file, nsbmd


def _srt_file(first_translation: int) -> bytes:
    channels = (0x30000010, 4096, 0x30000010, 4096, 0x20000010, 0x10000000, 0x30000010, 0)
    dummy = g3d_dictionary([("sol", bytes(40))])
    offset = 8 + len(dummy)
    track = g3d_dictionary([("sol", struct.pack("<10I", *channels, 0x10000010, offset))])
    animation = b"M\0AT" + struct.pack("<HH", 16, 0) + track + struct.pack("<16h", first_translation, *([0] * 15))
    root_size = len(g3d_dictionary([("animation", bytes(4))]))
    root = g3d_dictionary([("animation", struct.pack("<I", 8 + root_size))])
    block = b"SRT0" + struct.pack("<I", 8 + len(root) + len(animation)) + root + animation
    return nitro_file(b"BTA0", block)


def test_first_texture_translation_keeps_fx16_precision() -> None:
    source = read_nsbmd(nsbmd(bytes([1])), "modèle")
    changed = animation_first_frame(source, _srt_file(1024), "animation")
    material = changed.models[0].materials[0]
    assert material.texture_translation == (0, 1024)
    assert material.texture_scale == (4096, 4096)
    assert material.texture_rotation == (0, 4096)
    assert source.models[0].materials[0].texture_translation == (0, 0)


def _narc(second_end: int = 6) -> bytes:
    fat = b"BTAF" + struct.pack("<IHH4I", 28, 2, 0, 0, 3, 3, second_end)
    names = b"BTNF" + struct.pack("<I", 8)
    data = b"GMIF" + struct.pack("<I", 14) + b"abcdef"
    total = 16 + len(fat) + len(names) + len(data)
    return b"NARC" + struct.pack("<HHIHH", 0xFFFE, 0x0100, total, 16, 3) + fat + names + data


def test_narc_extracts_only_members_within_the_image_section() -> None:
    assert narc_members(_narc(), "archive") == (b"abc", b"def")
    with pytest.raises(ValueError, match="membre NARC 1 hors bornes"):
        narc_members(_narc(7), "archive")
    with pytest.raises(ValueError, match="archive NARC invalide"):
        narc_members(_narc()[:-1], "archive")
