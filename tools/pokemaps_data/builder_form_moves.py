"""Apprentissages de Deoxys selon la forme imposée par chaque cartouche GBA."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


def deoxys_move_versions(builder: DatabaseBuilder) -> dict[tuple, frozenset[int]]:
    forms = {"ruby": "normal", "sapphire": "normal", "emerald": "speed", "firered": "attack", "leafgreen": "defense"}
    versions = {
        (int(row["version_group_id"]), forms[row["identifier"]]): int(row["id"])
        for row in builder.version_rows
        if row["identifier"] in forms
    }
    pokemon = {
        int(row["id"]): row["identifier"].removeprefix("deoxys-")
        for row in builder.api.table("pokemon")
        if int(row["species_id"]) == 386
    }
    methods = {int(row["id"]): row["identifier"] for row in builder.api.table("pokemon_move_methods")}
    result: dict[tuple, set[int]] = {}
    for row in builder.api.table("pokemon_moves"):
        mon, vg = int(row["pokemon_id"]), int(row["version_group_id"])
        if mon not in pokemon or (vg, pokemon[mon]) not in versions:
            continue
        method = methods[int(row["pokemon_move_method_id"])]
        level = int(row["level"]) if method == "level-up" else 0
        key = (386, vg, int(row["move_id"]), method, level)
        matching = {
            int(version["id"])
            for version in builder.version_rows
            if int(version["version_group_id"]) == vg and forms.get(version["identifier"]) == pokemon[mon]
        }
        result.setdefault(key, set()).update(matching)
    return {key: frozenset(value) for key, value in result.items()}
