"""Façade des sources pret GBA ; Hoenn et les remakes conservent leurs variantes."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from .maps_terrain_gen3 import TerrainRules, terrain_rules
from .pret_gen3_maps import Gen3Layout, Gen3Map, read_layouts, read_maps
from .pret_gen3_offers import Gen3Offers
from .pret_gen3_rematches import TrainerRematches, read_rematches
from .pret_gen3_source import conditional_text, source_path
from .pret_gen3_tilesets import Gen3Tileset, read_tilesets
from .pret_gen3_trainers import Gen3Trainer, read_trainers
from .pret_gen3_wild import WildTable, wild_tables
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

    @cached_property
    def wild_tables(self) -> dict[str, tuple[WildTable, ...]]:
        return {version: wild_tables(self, version) for version, _ in self.versions}

    @cached_property
    def wild_methods(self) -> dict[str, frozenset[str]]:
        methods: dict[str, frozenset[str]] = {}
        for tables in self.wild_tables.values():
            for table in tables:
                methods[table.map_const] = methods.get(table.map_const, frozenset()) | {table.method}
        return methods

    @cached_property
    def terrain_rules(self) -> TerrainRules:
        return terrain_rules(self)

    @cached_property
    def trainers(self) -> dict[str, dict[str, Gen3Trainer]]:
        return {version: read_trainers(self, version) for version, _ in self.versions}

    @cached_property
    def rematches(self) -> dict[str, tuple[TrainerRematches, ...]]:
        return {version: read_rematches(self, version, self.trainers[version]) for version, _ in self.versions}

    @cached_property
    def offers(self) -> dict[str, Gen3Offers]:
        return {version: Gen3Offers(self, version) for version, _ in self.versions}
