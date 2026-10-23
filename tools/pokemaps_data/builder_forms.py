"""Profils de formes par cartouche : catalogue éditorial et statistiques PokéAPI épinglées."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

from .sources import DATA_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


def form_table(builder: DatabaseBuilder) -> list[tuple]:
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    pokemon = {row["identifier"]: int(row["id"]) for row in builder.api.table("pokemon")}
    species = {row["identifier"]: int(row["species_id"]) for row in builder.api.table("pokemon")}
    # Les formes purement visuelles (Cheniti, Sancoki, Arceus…) partagent la fiche de leur espèce.
    for form in builder.api.table("pokemon_forms"):
        key, base = form["identifier"], int(form["pokemon_id"])
        if key not in pokemon:
            pokemon[key] = base
            species[key] = next(int(r["species_id"]) for r in builder.api.table("pokemon") if int(r["id"]) == base)
    known_versions = {row["identifier"] for row in builder.api.table("versions")}
    stats: dict[int, dict[int, int]] = {}
    for row in builder.api.table("pokemon_stats"):
        stats.setdefault(int(row["pokemon_id"]), {})[int(row["stat_id"])] = int(row["base_stat"])
    result: list[tuple] = []
    with (DATA_DIR / "pokemon_forms.csv").open(encoding="utf-8", newline="") as source:
        for line, row in enumerate(csv.DictReader(source), 2):
            key = row["identifier"]
            if key not in pokemon or not row["name_fr"].strip():
                raise ValueError(f"pokemon_forms.csv:{line} : forme inconnue ou nom vide : {key}")
            profile = stats[pokemon[key]]
            if set(profile) != set(range(1, 7)):
                raise ValueError(f"pokemon_forms.csv:{line} : statistiques incomplètes : {key}")
            selected = set(row["versions"].split("|"))
            defaults = set(filter(None, row["default_versions"].split("|")))
            if not defaults <= selected or not selected <= known_versions or int(row["pokemon_id"]) != species[key]:
                raise ValueError(f"pokemon_forms.csv:{line} : espèce, version ou forme par défaut incohérente")
            for version in sorted(selected & versions.keys()):
                result.append(
                    (
                        versions[version],
                        int(row["pokemon_id"]),
                        key,
                        row["name_fr"],
                        row["sprite_folder"],
                        row["sprite_identifier"],
                        int(version in defaults),
                        line - 2,
                        *(profile[stat] for stat in range(1, 7)),
                    )
                )
    if any(game.pret_repo == "pokeheartgold" for game in builder.games):
        from .builder_pokemon_hgss import forms

        result.extend(forms())
    return sorted(result)
