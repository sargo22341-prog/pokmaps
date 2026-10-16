"""Corrections éditoriales explicites de noms de palettes absents des jeux de textures DS."""

from __future__ import annotations

import csv
from dataclasses import dataclass

from .pret_gen4_textures import NitroTextures
from .sources import DATA_DIR


@dataclass(frozen=True)
class PaletteBinding:
    family: str
    texture_set: int
    source: str
    target: str


def read_palette_bindings() -> tuple[PaletteBinding, ...]:
    result = []
    with (DATA_DIR / "map_texture_bindings_gen4.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), 2):
            if row["family"] not in ("platinum", "diamond-pearl") or row["kind"] != "palette" or not row["reason"]:
                raise ValueError(f"map_texture_bindings_gen4.csv:{line} : liaison invalide : {row}")
            value = PaletteBinding(row["family"], int(row["texture_set"]), row["source"], row["target"])
            if value in result:
                raise ValueError(f"map_texture_bindings_gen4.csv:{line} : liaison répétée")
            result.append(value)
    return tuple(result)


def bind_palettes(
    textures: NitroTextures, family: str, texture_set: int, bindings: tuple[PaletteBinding, ...]
) -> NitroTextures:
    palettes = dict(textures.palettes)
    for binding in bindings:
        if binding.family != family or binding.texture_set != texture_set:
            continue
        if binding.source in palettes or binding.target not in palettes:
            raise ValueError(f"correction de palette devenue invalide : {binding}")
        palettes[binding.source] = palettes[binding.target]
    return NitroTextures(textures.textures, palettes)
