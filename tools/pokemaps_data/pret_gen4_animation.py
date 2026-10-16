"""Première image des animations de textures Nitro, sans avancer l'état du jeu.

Les structures PAT0 et SRT0 sont relues contre les formats décrits par apicula (0BSD) ;
seule l'évaluation à l'image zéro est nécessaire au fond statique des cartes.
"""

from __future__ import annotations

from dataclasses import replace

from .pret_gen4_nitro import NitroFile
from .pret_gen4_nitro_container import blocks, dictionary
from .pret_gen4_source import ByteReader


def animation_first_frame(file: NitroFile, data: bytes, where: str) -> NitroFile:
    reader = ByteReader(data, where)
    signature = reader.slice(0, 4)
    if signature == b"BCA0":
        # Les poses de décor restent celles du modèle ; les animations articulées ne sont pas jouées.
        return file
    kinds = {b"BTP0": b"PAT0", b"BTA0": b"SRT0"}
    if signature not in kinds:
        raise ValueError(f"{where} : animation Nitro inconnue : {signature!r}")
    container = blocks(reader, signature)
    start = container[kinds[signature]]
    entries = dictionary(reader, start + 8)
    if len(entries) != 1:
        raise ValueError(f"{where} : une seule animation par archive est attendue")
    animation = start + reader.u32(entries[0][1])
    updates = _pattern(reader, animation) if signature == b"BTP0" else _srt(reader, animation)
    models = []
    for model in file.models:
        materials = tuple(
            replace(material, **updates[material.name]) if material.name in updates else material
            for material in model.materials
        )
        models.append(replace(model, materials=materials))
    return replace(file, models=tuple(models))


def _pattern(reader: ByteReader, start: int) -> dict[str, dict]:
    frames, texture_count, palette_count, textures, palettes = reader.unpack("HBBHH", start + 4)
    if not frames or not texture_count or not palette_count:
        raise ValueError(f"{reader.where} : animation de texture vide")
    texture_names = _names(reader, start + textures, texture_count)
    palette_names = _names(reader, start + palettes, palette_count)
    result = {}
    for name, entry in dictionary(reader, start + 12):
        count, _, offset = reader.unpack("IHH", entry)
        if not count or count > frames:
            raise ValueError(f"{reader.where} : piste PAT0 invalide : {name}")
        frame, texture, palette = reader.unpack("HBB", start + offset)
        if frame != 0 or texture >= texture_count or palette >= palette_count:
            raise ValueError(f"{reader.where} : première image PAT0 invalide : {name}")
        result[name] = {"texture": texture_names[texture], "palette": palette_names[palette]}
    return result


def _names(reader: ByteReader, start: int, count: int) -> tuple[str, ...]:
    return tuple(reader.slice(start + index * 16, 16).rstrip(b"\0").decode("latin-1") for index in range(count))


def _srt(reader: ByteReader, start: int) -> dict[str, dict]:
    if not reader.u16(start + 4):
        raise ValueError(f"{reader.where} : animation SRT0 vide")
    result = {}
    for name, entry in dictionary(reader, start + 8):
        values = tuple(_channel(reader, start, entry + index * 8, index == 2) for index in range(5))
        rotation = values[2]
        sine = rotation & 0xFFFF
        cosine = rotation >> 16 & 0xFFFF
        sine = sine - 65536 if sine >= 32768 else sine
        cosine = cosine - 65536 if cosine >= 32768 else cosine
        result[name] = {
            "texture_scale": values[:2],
            "texture_rotation": (sine, cosine),
            "texture_translation": values[3:],
        }
    return result


def _channel(reader: ByteReader, start: int, offset: int, rotation: bool) -> int:
    flags, value = reader.unpack("2I", offset)
    if not flags & 0xFFFF or flags & 0x0C000000:
        raise ValueError(f"{reader.where} : canal SRT0 invalide : {flags:#x}")
    if flags & 0x20000000:
        return value if rotation or value < 0x80000000 else value - 0x100000000
    if rotation:
        return reader.u32(start + value)
    return reader.s16(start + value) if flags & 0x10000000 else reader.s32(start + value)


def narc_members(data: bytes, where: str) -> tuple[bytes, ...]:
    reader = ByteReader(data, where)
    if reader.slice(0, 4) != b"NARC" or reader.u32(8) != len(data) or reader.u16(14) != 3:
        raise ValueError(f"{where} : archive NARC invalide")
    offset, chunks = reader.u16(12), {}
    for _ in range(3):
        kind, size = reader.slice(offset, 4), reader.u32(offset + 4)
        reader.require(offset, size)
        chunks[kind] = offset
        offset += size
    if set(chunks) != {b"BTAF", b"BTNF", b"GMIF"} or offset != len(data):
        raise ValueError(f"{where} : sections NARC inattendues")
    fat, image = chunks[b"BTAF"], chunks[b"GMIF"]
    count = reader.u16(fat + 8)
    if not 0 < count <= 1024:
        raise ValueError(f"{where} : nombre de membres NARC invalide : {count}")
    result = []
    end = image + reader.u32(image + 4)
    for index in range(count):
        first, last = reader.unpack("2I", fat + 12 + index * 8)
        if first > last or image + 8 + last > end:
            raise ValueError(f"{where} : membre NARC {index} hors bornes")
        result.append(reader.slice(image + 8 + first, last - first))
    return tuple(result)
