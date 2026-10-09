"""Conditions et indications des rencontres particulières de Hoenn."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .pret_hoenn_caves import moving_cave_areas

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_encounters import EncounterGroup


def complete_hoenn_encounters(builder: DatabaseBuilder, groups: list[EncounterGroup]) -> None:
    emerald = next((game for game in builder.games if game.version_group == "emerald"), None)
    if emerald is None:
        return
    repo = builder.gen3_repo(emerald, "les grottes à entrée mobile")
    routes = moving_cave_areas(repo)
    areas = builder.locations.area_keys
    league = next(
        int(row["id"])
        for row in builder.api.table("encounter_condition_values")
        if row["identifier"] == "story-progress-hall-of-fame"
    )
    version = next(int(row["id"]) for row in builder.version_rows if row["identifier"] == "emerald")
    for group in groups:
        if group.version_id != version:
            continue
        area = areas[group.location_area_id]
        if area in {"terra-cave/area", "marine-cave/area", "hoenn-battle-frontier/area"}:
            group.conditions = tuple(sorted({*group.conditions, league}))
        if area not in {"terra-cave/area", "marine-cave/area"}:
            continue
        numbers = ", ".join(const.removeprefix("MAP_ROUTE") for const, key in routes if key == area)
        group.notes.append(
            f"Entrée variable sur les Routes {numbers} ; consultez le scientifique de l'Institut Météo après la Ligue."
        )
