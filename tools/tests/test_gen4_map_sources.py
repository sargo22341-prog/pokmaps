"""En-têtes, caméras, éclairages et attaques DS lus dans des sources construites dans le test."""

import json
import struct
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_map_models import Gen4Header
from pokemaps_data.pret_gen4_maps import _camera, deg_to_index, fx32_const
from pokemaps_data.pret_gen4_maps_dp import _dp_header, _labelled_bytes, _split, read_light_file
from pokemaps_data.pret_gen4_moves import effect_key, read_gen4_moves

FIELDS = (
    "NARC_area_data_narc_0006_bin, 20, NARC_map_matrix_narc_0000_bin, NARC_scr_seq_release_narc_0002_bin, "
    "NARC_scr_seq_release_narc_0465_bin, NARC_msg_narc_0018_bin, SEQ_CITY01_D, SEQ_CITY01_N, "
    "ENCDATA(NARC_d_enc_data_narc_0003_bin, NARC_p_enc_data_narc_0004_bin), NARC_zone_event_release_narc_0002_bin, "
    "MAPSEC_JUBILIFE_CITY, 0, 0, 1, 2, TRUE, TRUE, FALSE, TRUE"
)


def test_diamond_pearl_header_fields_and_encounters_by_version() -> None:
    header = _dp_header(3, "MAP_JUBLIFE", _split(FIELDS), "map_header.c")
    assert isinstance(header, Gen4Header)
    assert (header.area, header.move_models, header.scripts, header.init_scripts, header.texts) == (6, 20, 2, 465, 18)
    assert header.encounters == (("diamond", 3), ("pearl", 4))
    assert (header.location, header.map_type, header.bike, header.escape_rope) == ("JUBILIFE_CITY", 1, True, False)
    without = FIELDS.replace("ENCDATA(NARC_d_enc_data_narc_0003_bin, NARC_p_enc_data_narc_0004_bin)", "0xFFFF")
    assert _dp_header(3, "MAP_JUBLIFE", _split(without), "map_header.c").encounters == ()
    with pytest.raises(ValueError, match="archive map_matrix attendue"):
        _dp_header(3, "MAP_JUBLIFE", _split(FIELDS.replace("map_matrix", "zone_event")), "map_header.c")
    with pytest.raises(ValueError, match="type de lieu inconnu : 9"):
        _dp_header(3, "MAP_JUBLIFE", _split(FIELDS.replace("0, 0, 1, 2", "0, 0, 9, 2")), "map_header.c")


def test_camera_table_bytes_and_platinum_camera_source(tmp_path: Path) -> None:
    record = struct.pack("<iHHHHBBHii", 0x29AEC1, 0xD602, 0, 0, 0, 0, 0, 0x5C1, 0x96000, 0x384000)
    lines = ", ".join(f"0x{byte:02X}" for byte in record)
    path = tmp_path / "camera.s"
    path.write_text(f"\t.section .rodata\n\n\t.global ov05_021F6608\nov05_021F6608: ; 0x0\n\t.byte {lines}\n\n_next:\n")
    assert _labelled_bytes(path, "ov05_021F6608") == record
    body = """
        .distance = FX32_CONST(666.922119140625),
        .cameraAngle = { -F32_DEG_TO_IDX(59.051513671875), 0, 0 },
        .projection = CAMERA_PROJECTION_PERSPECTIVE,
        .verticalFov = F32_DEG_TO_IDX(8.0914306640625),
        .nearPlaneDist = CAMERA_DEFAULT_NEAR_CLIP,
        .farPlaneDist = FX32_ONE * 900,"""
    camera = _camera(body, "field_camera.c")
    assert (camera.distance, camera.angle_x, camera.vertical_fov) == (0x29AEC1, 0xD602, 0x5C1)
    assert (camera.near, camera.far) == (0x96000, 0x384000)
    assert fx32_const("59.051513671875") == 241875 and deg_to_index("59.051513671875") == 10750


def test_diamond_pearl_lighting_text(tmp_path: Path) -> None:
    period = "{end},\r\n" + "1,11,11,16,1897,-3600,-466,\r\n" + "0,0,0,0,0,0,0,\r\n" * 3 + "14,14,16,\r\n" * 4 + "\r\n"
    path = tmp_path / "area00light.txt"
    path.write_text(period.format(end=0) + period.format(end=43200) + "EOF", newline="")
    periods = read_light_file(path)
    assert [p.end_time for p in periods] == [0, 43200]
    assert periods[0].lights[0].direction == (1897, -3600, -466) and periods[0].emission == (14, 14, 16)
    path.write_text(period.format(end=7200) + period.format(end=0) + "EOF", newline="")
    with pytest.raises(ValueError, match="heures de fin d'éclairage invalides"):
        read_light_file(path)


def test_move_effects_use_engine_numbers(tmp_path: Path) -> None:
    assert effect_key(6) == "006"
    with pytest.raises(ValueError, match="numéro d'effet DS invalide"):
        effect_key(-1)
    (tmp_path / "include/constants").mkdir(parents=True)
    (tmp_path / "include/constants/battle.h").write_text(
        "#define MOVE_EFFECT_NORMAL_HIT 0\n#define MOVE_EFFECT_PARALYZE_HIT 1\n"
    )
    (tmp_path / "files/poketool/waza").mkdir(parents=True)
    rows = [
        {"name": "MOVE_NONE", "effect": "MOVE_EFFECT_NORMAL_HIT", "power": 0, "pp": 0, "effectChance": 0},
        {"name": "MOVE_THUNDER_PUNCH", "effect": "MOVE_EFFECT_PARALYZE_HIT", "power": 75, "pp": 15, "effectChance": 10},
        {"name": "MOVE_ZAP_CANNON", "effect": "MOVE_EFFECT_PARALYZE_HIT", "power": 120, "pp": 5, "effectChance": 100},
    ]

    (tmp_path / "files/poketool/waza/waza_tbl.json").write_text(json.dumps({"waza_tbl": rows}))
    moves = read_gen4_moves(tmp_path)
    assert [(m.const, m.effect, m.chance_percent) for m in moves] == [
        ("THUNDER_PUNCH", "001", 10),
        ("ZAP_CANNON", "001", None),
    ]
