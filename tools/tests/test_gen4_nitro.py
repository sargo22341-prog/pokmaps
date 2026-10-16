"""Modèles, textures et listes d'affichage Nitro construits dans le test, sans cache ni réseau."""

import struct

import pytest

from pokemaps_data.pret_gen4_gx import QUADS, TRIANGLE_STRIP, TRIANGLES, primitives, triangles
from pokemaps_data.pret_gen4_nitro import _pivot_rotation, read_nsbmd
from pokemaps_data.pret_gen4_textures import OPAQUE, PALETTE_16, decode, read_nsbtx


def g3d_dictionary(entries: list[tuple[str, bytes]]) -> bytes:
    """Dictionnaire G3D : en-tête, arbre (non lu), entrées de même taille, noms de 16 octets."""
    count, unit = len(entries), len(entries[0][1])
    entries_offset = 8 + 4 * (count + 1)
    size = entries_offset + 4 + unit * count + 16 * count
    header = struct.pack("<BBHHH", 0, count, size, 8, entries_offset) + bytes(4 * (count + 1))
    body = struct.pack("<HH", unit, 4 + unit * count) + b"".join(data for _, data in entries)
    names = b"".join(name.encode().ljust(16, b"\0") for name, _ in entries)
    return header + body + names


def nitro_file(magic: bytes, block: bytes) -> bytes:
    return magic + struct.pack("<HHIHH", 0xFEFF, 1, 20 + len(block), 16, 1) + struct.pack("<I", 20) + block


# --- Textures -----------------------------------------------------------------------------------------------


def texture_block(parameters: int, texels: bytes, colors: tuple[int, ...], compressed: int = 0) -> bytes:
    texture_dict = g3d_dictionary([("herbe", struct.pack("<II", parameters, 0))])
    palette_dict = g3d_dictionary([("herbe_pl", struct.pack("<HH", 0, 0))])
    texture_dict_offset = 0x3C
    palette_dict_offset = texture_dict_offset + len(texture_dict)
    texel_offset = palette_dict_offset + len(palette_dict)
    palette_offset = texel_offset + len(texels)
    palette = struct.pack(f"<{len(colors)}H", *colors)
    header = bytearray(0x3C)
    header[0:4] = b"TEX0"
    struct.pack_into("<I", header, 4, palette_offset + len(palette))
    struct.pack_into("<H", header, 0x0E, texture_dict_offset)
    struct.pack_into("<I", header, 0x14, texel_offset)
    struct.pack_into("<H", header, 0x1C, compressed)
    struct.pack_into("<H", header, 0x30, len(palette) >> 3)
    struct.pack_into("<H", header, 0x34, palette_dict_offset)
    struct.pack_into("<I", header, 0x38, palette_offset)
    return bytes(header) + texture_dict + palette_dict + texels + palette


def palette16_parameters(transparent: bool) -> int:
    # Texture 8 × 8 au décalage 0, format 16 couleurs, couleur 0 transparente ou non.
    return (PALETTE_16 << 26) | (int(transparent) << 29)


def test_palette_texture_decodes_with_its_palette() -> None:
    texels = bytes([0x10] * 32)  # indices 0 puis 1 en alternance
    colors = (0x7FFF, 0x001F, 0, 0, 0, 0, 0, 0)
    textures = read_nsbtx(nitro_file(b"BTX0", texture_block(palette16_parameters(True), texels, colors)), "jeu")
    texture = textures.textures["herbe"]
    assert (texture.width, texture.height, texture.format) == (8, 8, PALETTE_16)
    pixels = decode(texture, textures.palettes["herbe_pl"])
    assert pixels[:2] == ((0, 0, 0, 0), (31, 0, 0, OPAQUE))
    opaque = read_nsbtx(nitro_file(b"BTX0", texture_block(palette16_parameters(False), texels, colors)), "jeu")
    assert decode(opaque.textures["herbe"], opaque.palettes["herbe_pl"])[0] == (31, 31, 31, OPAQUE)


def test_unused_texture_formats_and_missing_colors_are_refused() -> None:
    texels = bytes([0xAA] * 32)
    with pytest.raises(ValueError, match="compressées 4 × 4"):
        read_nsbtx(nitro_file(b"BTX0", texture_block(palette16_parameters(True), texels, (0,) * 8, 1)), "jeu")
    direct = (7 << 26) | (0 << 20)
    with pytest.raises(ValueError, match="format 7 non pris en charge"):
        read_nsbtx(nitro_file(b"BTX0", texture_block(direct, bytes(128), (0,) * 8)), "jeu")
    textures = read_nsbtx(nitro_file(b"BTX0", texture_block(palette16_parameters(False), texels, (0,) * 8)), "jeu")
    with pytest.raises(ValueError, match="couleur 10 hors de la palette"):
        decode(textures.textures["herbe"], textures.palettes["herbe_pl"])


def test_empty_prop_texture_set_and_wrong_container() -> None:
    assert read_nsbtx(bytes(4), "vide").textures == {}
    with pytest.raises(ValueError, match="fichier BTX0 attendu"):
        read_nsbtx(nitro_file(b"BMD0", b"TEX0" + bytes(4)), "jeu")


# --- Listes d'affichage --------------------------------------------------------------------------------------


def display_list(*commands: tuple[int, tuple[int, ...]]) -> bytes:
    data = b""
    for start in range(0, len(commands), 4):
        group = list(commands[start : start + 4])
        opcodes = [opcode for opcode, _ in group] + [0] * (4 - len(group))
        data += bytes(opcodes) + b"".join(struct.pack(f"<{len(p)}I", *p) for _, p in group)
    return data


def vertex16(x: int, y: int, z: int) -> tuple[int, tuple[int, ...]]:
    return 0x23, ((x & 0xFFFF) | (y & 0xFFFF) << 16, z & 0xFFFF)


def test_display_list_vertices_attributes_and_strips() -> None:
    data = display_list(
        (0x14, (3,)),
        (0x22, ((-16 & 0xFFFF) | 32 << 16,)),
        (0x40, (TRIANGLE_STRIP,)),
        vertex16(0, 0, 0),
        vertex16(-4096, 4096, 0),
        (0x28, (1 | (2 << 10) | ((-1 & 0x3FF) << 20),)),
        (0x26, (8 | (8 << 16),)),
        (0x41, ()),
    )
    [strip] = primitives(data, "forme")
    assert strip.kind == TRIANGLE_STRIP and len(strip.vertices) == 4
    assert strip.vertices[0].matrix == 3 and strip.vertices[0].texcoord == (-16, 32)
    assert strip.vertices[2].position == (-4095, 4098, -1)
    assert strip.vertices[3].position == (8, 4098, 8)
    first, second = triangles(strip)
    assert first == (strip.vertices[0], strip.vertices[1], strip.vertices[2])
    assert second[0] is strip.vertices[2] and second[1] is strip.vertices[1]


def test_display_list_refuses_unknown_commands_and_incomplete_primitives() -> None:
    with pytest.raises(ValueError, match="commande GX inconnue 0x50"):
        primitives(display_list((0x50, (0,))), "forme")
    with pytest.raises(ValueError, match="2 sommets pour une primitive"):
        primitives(display_list((0x40, (TRIANGLES,)), vertex16(0, 0, 0), vertex16(1, 1, 1), (0x41, ())), "forme")
    quad = display_list((0x40, (QUADS,)), *(vertex16(i, 0, 0) for i in range(4)), (0x41, ()))
    assert len(triangles(primitives(quad, "forme")[0])) == 2


# --- Modèles -------------------------------------------------------------------------------------------------


def materials_block() -> bytes:
    """Bloc des matériaux : dictionnaires des liaisons texture et palette vers le matériau 0, puis ses données."""
    material = struct.pack(
        "<HHIIIIIIHHHHii", 0, 0x2C, 0x1234, 0x5678, 0x1F, 0, PALETTE_16 << 26, 0, 0, 0, 8, 8, 4096, 4096
    )
    dictionary_size = len(g3d_dictionary([("sol", bytes(4))]))
    binding_size = len(g3d_dictionary([("herbe", bytes(4))]))
    texture_offset = 4 + dictionary_size
    palette_offset = texture_offset + binding_size
    index_list = palette_offset + binding_size
    block = struct.pack("<HH", texture_offset, palette_offset)
    block += g3d_dictionary([("sol", struct.pack("<I", index_list + 4))])
    block += g3d_dictionary([("herbe", struct.pack("<HBB", index_list, 1, 1))])
    block += g3d_dictionary([("herbe_pl", struct.pack("<HBB", index_list, 1, 1))])
    return block + bytes(4) + material


def model_bytes(sbc: bytes) -> bytes:
    """Modèle d'un nœud, d'un matériau lié à « herbe » / « herbe_pl » et d'une forme d'un triangle."""
    node_size = len(g3d_dictionary([("racine", bytes(4))]))
    nodes = g3d_dictionary([("racine", struct.pack("<I", node_size))]) + struct.pack("<Hh", 0x7, 4096)
    sbc = sbc + bytes(-len(sbc) % 4)
    materials = materials_block()
    triangle = display_list((0x40, (TRIANGLES,)), vertex16(0, 0, 0), vertex16(1, 0, 0), vertex16(0, 0, 1), (0x41, ()))
    shape_size = len(g3d_dictionary([("forme", bytes(4))]))
    shapes = g3d_dictionary([("forme", struct.pack("<I", shape_size))])
    shapes += struct.pack("<HHIII", 0, 16, 0, 16, len(triangle)) + triangle
    sbc_offset = 0x40 + len(nodes)
    material_start = sbc_offset + len(sbc)
    shape_start = material_start + len(materials)
    info = struct.pack("<8Bii4H6hii", 0, 0, 0, 1, 1, 1, 0, 0, 4096, 4096, 3, 1, 1, 0, 0, 0, 0, 1, 1, 1, 4096, 4096)
    header = struct.pack("<5I", shape_start + len(shapes), sbc_offset, material_start, shape_start, 0)
    return header + info + nodes + sbc + materials + shapes


def nsbmd(sbc: bytes) -> bytes:
    model = model_bytes(sbc)
    size = len(g3d_dictionary([("bloc", bytes(4))]))
    models = g3d_dictionary([("bloc", struct.pack("<I", 8 + size))])
    block = b"MDL0" + struct.pack("<I", 8 + len(models) + len(model)) + models + model
    return nitro_file(b"BMD0", block)


def test_model_nodes_materials_shapes_and_render_commands() -> None:
    sbc = bytes([0x06, 0, 0xFF, 0, 0x04, 0, 0x05, 0, 0x01])
    [model] = read_nsbmd(nsbmd(sbc), "modèle").models
    assert model.name == "bloc" and model.position_scale == 4096
    assert model.nodes[0].rotation == (4096, 0, 0, 0, 4096, 0, 0, 0, 4096)
    material = model.materials[0]
    assert (material.name, material.texture, material.palette) == ("sol", "herbe", "herbe_pl")
    assert (material.diffuse_ambient, material.polygon_attributes) == (0x1234, 0x1F)
    assert len(triangles(primitives(model.shapes[0].display_list, "forme")[0])) == 1
    assert [command.opcode for command in model.render] == [0x06, 0x04, 0x05, 0x01]


def test_render_commands_end_with_ret_and_known_opcodes() -> None:
    with pytest.raises(ValueError, match="commande de rendu inconnue 0x1f"):
        read_nsbmd(nsbmd(bytes([0x1F, 0x01])), "modèle")
    with pytest.raises(ValueError, match="sans RET"):
        read_nsbmd(nsbmd(bytes([0x04, 0])), "modèle")


def test_compact_rotation_uses_the_sdk_pivot_table() -> None:
    # Pivot 0, signe négatif sur le pivot, C = -B : rotation de 90° autour de x.
    flag = (0 << 4) | 0x100 | 0x200
    assert _pivot_rotation(flag, 0, 4096) == (-4096, 0, 0, 0, 0, 4096, 0, -4096, 0)
