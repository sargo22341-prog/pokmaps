"""Lecteurs binaires DS sur des extraits construits dans le test, sans cache ni réseau."""

import struct
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_encounter_tables import TABLE_SIZE, compiled_table, json_table
from pokemaps_data.pret_gen4_land import (
    DiamondBdhc,
    PlatinumBdhc,
    fx_div,
    fx_mul,
    heights,
    read_land_block,
)
from pokemaps_data.pret_gen4_narc import _matrix, members, read_compiled_events
from pokemaps_data.pret_gen4_source import ByteReader, c_defines, c_enum, metang_enum, read_json

# --- Sources communes ----------------------------------------------------------------------------------------


def test_byte_reader_refuses_reads_outside_the_buffer() -> None:
    reader = ByteReader(b"\x01\x02\x03", "extrait")
    assert reader.u16(0) == 0x0201
    with pytest.raises(ValueError, match="extrait : lecture de 2 octets à 0x2 hors du fichier"):
        reader.u16(2)


def test_metang_enum_follows_aliases_and_explicit_values(tmp_path: Path) -> None:
    path = tmp_path / "flags.txt"
    path.write_text("FLAG_A\nSTART\nFLAG_B = START\nFLAG_C\nVARS_START = 16384\nVAR_A = VARS_START\nVAR_B\n")
    assert metang_enum(path) == {
        "FLAG_A": 0,
        "START": 1,
        "FLAG_B": 1,
        "FLAG_C": 2,
        "VARS_START": 16384,
        "VAR_A": 16384,
        "VAR_B": 16385,
    }
    path.write_text("A\nA\n")
    with pytest.raises(ValueError, match="constante répétée"):
        metang_enum(path)


def test_c_constants_read_enums_and_simple_sums(tmp_path: Path) -> None:
    path = tmp_path / "constants.h"
    path.write_text(
        "enum MapType {\n    MAP_TYPE_NONE = 0, // vide\n    MAP_TYPE_TOWN,\n    MAP_TYPE_CAVE = 3,\n};\n"
        "#define WEATHER_CLEAR 0\n#define WEATHER_START 32\n#define WEATHER_SNOW (WEATHER_START + 4)\n"
        "#define WEATHER_COUNT (WEATHER_SNOW - WEATHER_START)\n"
    )
    assert c_enum(path, "MapType") == {"MAP_TYPE_NONE": 0, "MAP_TYPE_TOWN": 1, "MAP_TYPE_CAVE": 3}
    assert c_defines(path, "WEATHER_") == {
        "WEATHER_CLEAR": 0,
        "WEATHER_START": 32,
        "WEATHER_SNOW": 36,
        "WEATHER_COUNT": 4,
    }
    path.write_text("#define WEATHER_START 32\n#define WEATHER_X (WEATHER_START * 2)\n")
    with pytest.raises(ValueError, match="expression non prise en charge"):
        c_defines(path, "WEATHER_")


def test_json_must_be_an_object(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("[1, 2]")
    with pytest.raises(ValueError, match="objet JSON attendu"):
        read_json(path)


def test_members_need_a_continuous_numbering(tmp_path: Path) -> None:
    for name in ("narc_0000.bin", "narc_0001.NSBTX", ".knarcignore"):
        (tmp_path / name).write_bytes(b"")
    assert sorted(members(tmp_path)) == [0, 1]
    (tmp_path / "narc_0003.bin").write_bytes(b"")
    with pytest.raises(ValueError, match="numérotation des membres incomplète"):
        members(tmp_path)


# --- Matrices, événements et rencontres compilés --------------------------------------------------------------


def test_compiled_matrix_with_headers_and_altitudes() -> None:
    data = bytes([2, 1, 1, 1, 3]) + b"map" + struct.pack("<2H", 5, 6) + bytes([1, 2]) + struct.pack("<2H", 10, 0xFFFF)
    matrix = _matrix(7, ByteReader(data, "matrice"))
    assert (matrix.name, matrix.blocks, matrix.headers, matrix.altitudes) == (
        "map",
        ((10, 0xFFFF),),
        ((5, 6),),
        ((1, 2),),
    )
    with pytest.raises(ValueError, match="octets en trop"):
        _matrix(7, ByteReader(data + b"\0", "matrice"))


def _events_bytes(warp_padding: int = 0) -> bytes:
    bg = struct.pack("<I", 1) + struct.pack("<HHiiiHH", 8201, 2, 107, 893, 0, 0, 0)
    obj = struct.pack("<I", 1) + struct.pack("<14Hi", 0, 14, 5, 0, 0, 3000, 2, 1, 2, 3, 1, 0, 119, 878, 0x10000)
    warp = struct.pack("<I", 1) + struct.pack("<HHHHI", 105, 875, 412, 0, warp_padding)
    coord = struct.pack("<I", 1) + struct.pack("<8H", 4, 108, 867, 8, 1, 0, 1, 0x4000)
    return bg + obj + warp + coord


def test_compiled_events_follow_the_platinum_event_format() -> None:
    events = read_compiled_events(3, ByteReader(_events_bytes(), "événements"))
    assert events.bg_events[0].script == 8201
    assert events.object_events[0].data == (1, 2, 3)
    assert events.object_events[0].y == 0x10000
    assert (events.warp_events[0].destination_header, events.coord_events[0].var) == (412, 0x4000)
    with pytest.raises(ValueError, match="remplissage non nul"):
        read_compiled_events(3, ByteReader(_events_bytes(warp_padding=1), "événements"))
    with pytest.raises(ValueError, match="octets après les événements"):
        read_compiled_events(3, ByteReader(_events_bytes() + b"\0", "événements"))


def _encounter_json() -> dict:
    def water(species: str) -> list[dict]:
        return [{"level_max": 30, "level_min": 20, "species": species}] * 5

    data: dict = {
        "land_rate": 30,
        "land_encounters": [{"level": 2, "species": "SPECIES_STARLY"}] * 12,
        "swarms": ["SPECIES_DODUO"] * 2,
        "day": ["SPECIES_STARLY", "SPECIES_BIDOOF"],
        "night": ["SPECIES_BIDOOF"] * 2,
        "radar": ["SPECIES_DODUO"] * 4,
        "surf_rate": 10,
        "surf_encounters": water("SPECIES_BIDOOF"),
        "map_category": "route",
    }
    data |= {f"rate_form{i}": 0 for i in range(5)} | {"unown_table": 0}
    data |= {version: ["SPECIES_STARLY", "SPECIES_DODUO"] for version in ("ruby", "sapphire", "emerald")}
    data |= {version: ["SPECIES_DODUO", "SPECIES_BIDOOF"] for version in ("firered", "leafgreen")}
    for rod in ("old", "good", "super"):
        data |= {f"{rod}_rod_rate": 25, f"{rod}_rod_encounters": water("SPECIES_DODUO")}
    return data


def _compile_encounters(data: dict, species: dict[str, int]) -> bytes:
    """Compilation de tools/jsoncnv/encounter.py de Platine, réécrite pour le test."""
    words = [data["land_rate"]] + [
        v for slot in data["land_encounters"] for v in (slot["level"], species[slot["species"]])
    ]
    words += [species[name] for key in ("swarms", "day", "night", "radar") for name in data[key]]
    words += [data[f"rate_form{i}"] for i in range(5)] + [data["unown_table"]]
    words += [species[n] for v in ("ruby", "sapphire", "emerald", "firered", "leafgreen") for n in data[v]]

    def water(key: str) -> bytes:
        return b"".join(
            struct.pack("<BBHI", s["level_max"], s["level_min"], 0, species[s["species"]]) for s in data[key]
        )

    result = struct.pack(f"<{len(words)}I", *words) + struct.pack("<I", data["surf_rate"]) + water("surf_encounters")
    result += bytes(44)
    for rod in ("old", "good", "super"):
        result += struct.pack("<I", data[f"{rod}_rod_rate"]) + water(f"{rod}_rod_encounters")
    return result


def test_json_and_compiled_encounter_tables_give_the_same_structure() -> None:
    species = {"SPECIES_NONE": 0, "SPECIES_DODUO": 84, "SPECIES_STARLY": 396, "SPECIES_BIDOOF": 399}
    data = _encounter_json()
    compiled = _compile_encounters(data, species)
    assert len(compiled) == TABLE_SIZE
    table = compiled_table(ByteReader(compiled, "rencontres"))
    assert table == json_table(data, species, "rencontres")
    assert table.day == (396, 399) and dict(table.gba)["firered"] == (84, 399)
    with pytest.raises(ValueError, match="remplissage non nul après le surf"):
        compiled_table(ByteReader(compiled[:250] + b"\1" + compiled[251:], "rencontres"))
    with pytest.raises(ValueError, match="champs de rencontres inconnus"):
        json_table(data | {"inconnu": 1}, species, "rencontres")


# --- Blocs de terrain et hauteurs -----------------------------------------------------------------------------


def _platinum_bdhc() -> bytes:
    # Une plaque horizontale à 16 unités sur tout le bloc : deux points, une normale (0, 1, 0), une constante.
    points = struct.pack("<4i", -256 << 12, -256 << 12, 256 << 12, 256 << 12)
    return (
        b"BDHC"
        + struct.pack("<6H", 2, 1, 1, 1, 1, 1)
        + points
        + struct.pack("<3i", 0, 4096, 0)
        + struct.pack("<i", -16 << 12)
        + struct.pack("<4H", 0, 1, 0, 0)
        + struct.pack("<iHH", 256 << 12, 1, 0)
        + struct.pack("<H", 0)
    )


def _block(bdhc: bytes, props: bytes = b"") -> bytes:
    attributes = struct.pack("<1024H", *([0x8002] + [0] * 1023))
    model = b"BMD0" + bytes(12)
    return struct.pack("<4I", len(attributes), len(props), len(model), len(bdhc)) + attributes + props + model + bdhc


def test_platinum_block_reads_attributes_props_and_heights(tmp_path: Path) -> None:
    prop = struct.pack("<12i", 23, 1, 2, 3, 0, 0, 0, 4096, 4096, 4096, 0, 0)
    path = tmp_path / "map_data_000.bin"
    path.write_bytes(_block(_platinum_bdhc(), prop + b"\r\n"))
    block = read_land_block(path, diamond_pearl=False)
    assert block.collision(0, 0) and block.behavior(0, 0) == 2 and not block.collision(1, 0)
    assert block.props[0].model == 23 and len(block.props) == 1
    assert isinstance(block.bdhc, PlatinumBdhc)
    assert heights(block.bdhc, 8 << 12, -8 << 12) == (16 << 12,)
    assert heights(block.bdhc, 300 << 12, 0) == ()


def _diamond_bdhc(constant: int = -16 << 12) -> bytes:
    vertices = [(-256, 16, -256), (256, 16, -256), (256, 16, 256)]
    header = struct.pack("<I18H", 32, 12, 3, 12, 1, 12, 1, 28, 2, 1, 10, 1, 1, 10, 0, 2, 0, 1, 1)
    prelude = struct.pack("<6i", -256 << 12, -256 << 12, 256 << 12, 256 << 12, 512 << 12, 512 << 12)
    body = b"".join(struct.pack("<3i", x << 12, y << 12, z << 12) for x, y, z in vertices)
    body += struct.pack("<3i", 0, 4096, 0) + struct.pack("<4Hi", 0, 1, 2, 0, constant)
    body += struct.pack("<HH", 1, 0) + struct.pack("<HiI", 1, 256 << 12, 0) + struct.pack("<H", 0)
    return b"BDHC" + header + prelude + body


def test_diamond_pearl_bdhc_triangles_and_their_planes(tmp_path: Path) -> None:
    path = tmp_path / "narc_0000.bin"
    path.write_bytes(_block(_diamond_bdhc()))
    bdhc = read_land_block(path, diamond_pearl=True).bdhc
    assert isinstance(bdhc, DiamondBdhc)
    assert heights(bdhc, 100 << 12, -100 << 12) == (16 << 12,)
    assert heights(bdhc, -100 << 12, 100 << 12) == ()
    path.write_bytes(_block(_diamond_bdhc(constant=-40 << 12)))
    with pytest.raises(ValueError, match="sommet hors du plan"):
        read_land_block(path, diamond_pearl=True)
    path.write_bytes(_block(_diamond_bdhc()[:-2]))
    with pytest.raises(ValueError, match="BDHC tronqué"):
        read_land_block(path, diamond_pearl=True)


def test_block_sizes_must_cover_the_file(tmp_path: Path) -> None:
    path = tmp_path / "map_data_000.bin"
    path.write_bytes(_block(_platinum_bdhc()) + b"\0")
    with pytest.raises(ValueError, match="tailles de bloc incohérentes"):
        read_land_block(path, diamond_pearl=False)


def test_fixed_point_arithmetic_matches_the_nitro_sdk() -> None:
    assert fx_mul(4096, 4096) == 4096
    assert fx_mul(-3, 2048) == -1
    assert fx_div(-16 << 12, 4096) == -16 << 12
    assert fx_div(1, 3) == 1365
    assert fx_div(-1, 3) == -1365
