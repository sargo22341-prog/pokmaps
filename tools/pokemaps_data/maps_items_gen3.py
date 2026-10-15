"""Projection des objets GBA à position fixe sur les cartes de l'aperçu PC."""

from __future__ import annotations

import re
from dataclasses import replace

from .maps_characters import ObjectRow
from .maps_layout_gen3 import Gen3GameMaps
from .pret_gen3_items import Gen3MapItem, map_items
from .pret_identifiers import item_identifier


def item_rows(maps: Gen3GameMaps) -> tuple[list[ObjectRow], tuple[Gen3MapItem, ...]]:
    rows, metadata = [], []
    for version, _ in maps.game.pret_versions:
        reader = maps.repo.offers[version]
        for const in sorted(maps.placements):
            for item in map_items(maps.maps[const], version, reader):
                point = maps.point(const, item.x, item.y)
                metadata.append(replace(item, x=point[0], y=point[1]))
                if item.kind == "hidden_coins":
                    # Comme au Casino de la 1re génération : un objet caché « Jetons » nommé par sa quantité.
                    coins = f"{item.quantity} jetons"
                    rows.append(
                        ObjectRow(
                            const, "hidden_item", *point, None, "coin", None, None, None, version=version, name_fr=coins
                        )
                    )
                    continue
                name = _identifier(item.item, reader.scripts.constants)
                rows.append(ObjectRow(const, item.kind, *point, None, name, None, None, None, version=version))
    return rows, tuple(metadata)


def _identifier(item: str, constants: dict[str, int]) -> str:
    number = constants[item]
    machines = {
        match[1].lower()
        for name, value in constants.items()
        if value == number and (match := re.match(r"ITEM_((?:TM|HM)\d{2})(?:_|$)", name))
    }
    if machines:
        if len(machines) != 1:
            raise ValueError(f"Machine ambiguë : {item}, {sorted(machines)}")
        return next(iter(machines))
    return item_identifier(item.removeprefix("ITEM_"), {})
