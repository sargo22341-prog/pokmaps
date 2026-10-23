"""Identités de lieux natifs HGSS, indépendantes du découpage des zones PokéAPI."""

import csv
from dataclasses import dataclass

from .sources import DATA_DIR


@dataclass(frozen=True)
class NativeLocation:
    header: int
    identifier: str
    name_fr: str
    region: int | None

    @property
    def location_id(self) -> int:
        return 20_000 + self.header

    @property
    def area_id(self) -> int:
        return 30_000 + self.header


def locations() -> tuple[NativeLocation, ...]:
    with (DATA_DIR / "hgss_maps.csv").open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    result = tuple(
        NativeLocation(
            int(row["header"]),
            "hgss-" + row["const"].removeprefix("MAP_").lower().replace("_", "-"),
            row["name_fr"],
            {"johto": 2, "kanto": 1, "special": None}[row["scope"]],
        )
        for row in rows
        if row["scope"] != "excluded"
    )
    if len(result) != 496 or len({r.header for r in result}) != len(result) or any(not r.name_fr for r in result):
        raise ValueError("HGSS : identités des lieux natifs incomplètes ou répétées")
    return result
