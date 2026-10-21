"""Fixtures minimales des formats HGSS : aucun cache ni réseau dans les tests ordinaires."""

import struct
from pathlib import Path

import pytest

from pokemaps_data import preview_maps_hgss
from pokemaps_data.pret_gen4_land import FX_ONE, heights
from pokemaps_data.pret_hgss_binary import read_archive, read_land, read_matrix
from pokemaps_data.pret_hgss_maps import HgssMapRepo, _actor, _warp
from pokemaps_data.preview_maps_hgss import _point


def _narc(payload: bytes) -> bytes:
    table = struct.pack("<4sIHHII", b"BTAF", 20, 1, 0, 0, len(payload))
    names = struct.pack("<4sI", b"BTNF", 8)
    image = struct.pack("<4sI", b"GMIF", 8 + len(payload)) + payload
    return (
        struct.pack("<4sHHIHH", b"NARC", 0xFFFE, 0x100, 16 + len(table + names + image), 16, 3) + table + names + image
    )


def _bdhc() -> bytes:
    header = b"BDHC" + struct.pack("<6H", 2, 1, 2, 2, 0, 0)
    corners = struct.pack("<4i", -256 * FX_ONE, -256 * FX_ONE, 256 * FX_ONE, 256 * FX_ONE)
    normal = struct.pack("<3i", 0, FX_ONE, 0)
    constants = struct.pack("<2i", 0, -16 * FX_ONE)
    plates = struct.pack("<8H", 0, 1, 0, 0, 0, 1, 0, 1)
    return header + corners + normal + constants + plates


def _land() -> bytes:
    attributes = struct.pack("<1024H", 0x8001, *([0] * 1023))
    auxiliary = b"EXTR"
    prop = struct.pack("<12i", 7, 1, 2, 3, 0, 0, 0, FX_ONE, FX_ONE, FX_ONE, 0, 0)
    model = b"BMD0"
    return (
        struct.pack("<4I2H", len(attributes), len(prop), len(model), len(_bdhc()), 0x1234, len(auxiliary))
        + attributes
        + auxiliary
        + prop
        + model
        + _bdhc()
    )


def test_archive_returns_exact_member_and_rejects_out_of_bounds(tmp_path: Path) -> None:
    path = tmp_path / "archive.narc"
    path.write_bytes(_narc(b"native"))
    assert read_archive(path) == (b"native",)
    bad = bytearray(path.read_bytes())
    struct.pack_into("<I", bad, 32, 500)
    path.write_bytes(bad)
    with pytest.raises(ValueError, match="hors du fichier"):
        read_archive(path)


@pytest.mark.parametrize("change", [0, 8, 16, 20])
def test_archive_rejects_invalid_header_or_section(tmp_path: Path, change: int) -> None:
    data = bytearray(_narc(b"x"))
    data[change] ^= 0xFF
    path = tmp_path / "bad.narc"
    path.write_bytes(data)
    with pytest.raises(ValueError, match="NARC"):
        read_archive(path)


def test_matrix_preserves_native_headers_altitudes_and_blocks() -> None:
    data = struct.pack("<5B", 2, 1, 1, 1, 3) + b"T20" + struct.pack("<2H2B2H", 60, 33, 2, 3, 0, 1)
    matrix = read_matrix(data, 0, "fixture matrice")
    assert matrix.name == "T20"
    assert matrix.headers == ((60, 33),)
    assert matrix.altitudes == ((2, 3),)
    assert matrix.blocks == ((0, 1),)
    with pytest.raises(ValueError, match="taille de matrice"):
        read_matrix(data + b"x", 0, "fixture matrice")


@pytest.mark.parametrize("data", [b"", bytes((0, 1, 0, 0, 0)), bytes((1, 1, 2, 0, 0)), bytes((255, 255, 0, 0, 0))])
def test_invalid_matrix_is_a_visible_error(data: bytes) -> None:
    with pytest.raises(ValueError, match="fixture"):
        read_matrix(data, 0, "fixture")


def test_land_extra_section_does_not_shift_collision_props_or_surfaces() -> None:
    block = read_land(_land(), "fixture terrain")
    assert block.collision(0, 0) and block.behavior(0, 0) == 1
    assert not block.collision(1, 0)
    assert block.props[0].model == 7
    assert block.props[0].position == (1, 2, 3)
    assert block.model == b"BMD0"
    assert block.bdhc is not None
    assert heights(block.bdhc, 0, 0) == (0, 16 * FX_ONE)


@pytest.mark.parametrize("change", [0, 4, 8, 12, 16, 18])
def test_land_rejects_sinnoh_header_and_inconsistent_sizes(change: int) -> None:
    data = bytearray(_land())
    data[change] ^= 1
    with pytest.raises(ValueError, match="terrain HGSS"):
        read_land(data, "fixture terrain HGSS")


def test_warp_preserves_height_and_requires_resolved_destination() -> None:
    row = {"x": 684, "z": 393, "y": 16, "header": "MAP_LAB", "anchor": 0}
    warp = _warp(row, {"MAP_LAB": 61}, "fixture")
    assert (warp.x, warp.z, warp.y, warp.destination, warp.anchor) == (684, 393, 16, 61, 0)
    with pytest.raises(ValueError, match="passage HGSS invalide"):
        _warp(row, {}, "fixture")
    with pytest.raises(ValueError, match="coordonnées"):
        _warp(row | {"x": -1}, {"MAP_LAB": 61}, "fixture")


def test_actor_keeps_native_script_flag_direction_and_units() -> None:
    row = {
        "id": "doctor",
        "spriteId": "SPRITE_DOCTOR",
        "movement": 0,
        "type": 0,
        "eventFlag": "FLAG_HIDE_ELM",
        "scriptId": "_EV_000 + 1",
        "facingDirection": 1,
        "param0": 0,
        "param1": 0,
        "param2": 0,
        "xRange": 0,
        "yRange": 0,
        "x": 6,
        "z": 5,
        "y": 0,
    }
    actor = _actor(row, "fixture")
    assert (actor.script, actor.flag, actor.direction) == ("_EV_000 + 1", "FLAG_HIDE_ELM", 1)
    assert (actor.x, actor.z, actor.y) == (6, 5, 0)
    with pytest.raises(ValueError, match="acteur HGSS invalide"):
        _actor(row | {"facingDirection": "1"}, "fixture")
    with pytest.raises(ValueError, match="direction"):
        _actor(row | {"facingDirection": 4}, "fixture")


def test_projection_uses_global_tiles_fx32_height_and_pixel_origin() -> None:
    assert _point(684, 393, 16 * FX_ONE, (10624, 5888), FX_ONE) == (328, 392)


def test_other_versions_cannot_enter_hgss_reader(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="version HGSS invalide"):
        HgssMapRepo(tmp_path, "platinum")


def _failed_version(root: Path, output: Path, version: str) -> dict:
    raise ValueError(f"{root} {output} {version} : format non pris en charge")


def test_failed_proof_preserves_previous_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "preview/hgss-maps"
    target.mkdir(parents=True)
    previous = target / "previous-proof.json"
    previous.write_text("preuve valide", encoding="utf-8")
    monkeypatch.setattr(preview_maps_hgss, "validate_sources", lambda root: {})
    monkeypatch.setattr(preview_maps_hgss, "_version", _failed_version)
    with pytest.raises(ValueError, match="format non pris en charge"):
        preview_maps_hgss.build_hgss_maps(tmp_path / "cache", target.parent)
    assert previous.read_text(encoding="utf-8") == "preuve valide"
