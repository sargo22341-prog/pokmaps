"""En-tête commun des fichiers Nitro (NSBMD, NSBTX…) et dictionnaires de ressources G3D."""

from __future__ import annotations

from .pret_gen4_source import ByteReader

_NAME_SIZE = 16
_MAX_DICTIONARY_ENTRIES = 255


def blocks(reader: ByteReader, magic: bytes) -> dict[bytes, int]:
    """Blocs d'un fichier Nitro (en-tête commun aux NSBMD, NSBTX, NSBTA…) : signature -> début du bloc."""
    if reader.slice(0, 4) != magic or reader.u16(4) != 0xFEFF:
        raise ValueError(f"{reader.where} : fichier {magic.decode()} attendu")
    size, header, count = reader.u32(8), reader.u16(12), reader.u16(14)
    if size != len(reader.data) or header != 16 or not 0 < count <= 8:
        raise ValueError(f"{reader.where} : en-tête Nitro incohérent")
    found = {}
    for offset in reader.unpack(f"{count}I", 16):
        kind = reader.slice(offset, 4)
        if kind in found:
            raise ValueError(f"{reader.where} : bloc {kind!r} répété")
        reader.require(offset, reader.u32(offset + 4))
        found[kind] = offset
    return found


def dictionary(reader: ByteReader, offset: int) -> list[tuple[str, int]]:
    """Dictionnaire G3D : (nom, début des données de l'entrée) dans l'ordre du fichier."""
    revision, count = reader.u8(offset), reader.u8(offset + 1)
    if revision != 0 or count > _MAX_DICTIONARY_ENTRIES:
        raise ValueError(f"{reader.where} : dictionnaire invalide à {offset:#x}")
    entries = offset + reader.u16(offset + 6)
    unit, names = reader.u16(entries), entries + reader.u16(entries + 2)
    result = []
    for i in range(count):
        raw = reader.slice(names + _NAME_SIZE * i, _NAME_SIZE)
        result.append((raw.rstrip(b"\0").decode("latin-1"), entries + 4 + i * unit))
    return result
