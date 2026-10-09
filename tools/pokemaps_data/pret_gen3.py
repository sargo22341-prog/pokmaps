"""Façade des sources pret GBA ; Hoenn et les remakes conservent leurs variantes."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from .pret_gen3_maps import Gen3Layout, Gen3Map, read_layouts, read_maps
from .pret_gen3_source import conditional_text, source_path
from .pret_gen3_tilesets import Gen3Tileset, read_tilesets
from .pret_moves import PretMove


class Gen3PretRepo:
    def __init__(self, root: Path, versions: tuple[tuple[str, str], ...]) -> None:
        symbols = frozenset(symbol for _, symbol in versions)
        if len(versions) != len(symbols) or any(version != symbol.lower() for version, symbol in versions):
            raise ValueError(f"{root} : versions GBA invalides : {versions}")
        if symbols not in (
            frozenset({"RUBY", "SAPPHIRE"}),
            frozenset({"EMERALD"}),
            frozenset({"FIRERED", "LEAFGREEN"}),
        ):
            raise ValueError(f"{root} : versions GBA invalides : {versions}")
        self.root = root
        self.versions = versions
        self.ruby = "RUBY" in symbols
        self.remake = "FIRERED" in symbols

    def source_text(self, relative: str, version: str) -> str:
        """Source sélectionnée pour une version, en anglais, révision 0 et sans options de correction."""
        symbols = dict(self.versions)
        if version not in symbols:
            raise ValueError(f"{self.root} : version inconnue : {version}")
        return conditional_text(source_path(self.root, relative), frozenset({"ENGLISH", symbols[version]}))

    @cached_property
    def layouts(self) -> dict[str, Gen3Layout]:
        return read_layouts(self.root)

    @cached_property
    def maps(self) -> dict[str, Gen3Map]:
        return read_maps(self.root, self.layouts)

    @cached_property
    def headers(self) -> dict[str, Gen3Map]:
        return self.maps

    @cached_property
    def tilesets(self) -> dict[str, Gen3Tileset]:
        return read_tilesets(self.root, self.ruby, self.remake)

    @cached_property
    def moves(self) -> list[PretMove]:
        from .pret_gen3_moves import read_moves

        return read_moves(self.root)
