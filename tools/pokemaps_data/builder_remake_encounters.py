"""Lettres de Tanoby et conditions d'accès particulières des remakes de Kanto."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import TYPE_CHECKING

from .maps import read_map_areas
from .pret_remake_encounters import roaming_starters, unown_chambers

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_encounters import EncounterGroup
    from .pret_gen3 import Gen3PretRepo


def complete_remake_encounters(builder: DatabaseBuilder, groups: list[EncounterGroup]) -> None:
    game = next((game for game in builder.games if game.version_group == "firered-leafgreen"), None)
    if game is None:
        return
    repo = builder.gen3_repo(game, "les rencontres particulières des remakes")
    notes = _chamber_notes(repo)
    conditions = {row["identifier"]: int(row["id"]) for row in builder.api.table("encounter_condition_values")}
    species = {value: row["identifier"] for value, row in builder.species.items()}
    versions = {int(row["id"]): row["identifier"] for row in builder.version_rows}
    choices = {version: roaming_starters(repo, version) for version, _ in game.pret_versions}
    _complete_roaming_methods(builder, groups, set(choices))
    areas = builder.locations.area_keys
    sevii = {
        key
        for const, key in read_map_areas(game.version_group)[game.map_family]
        if const.startswith(("MAP_FOUR_ISLAND", "MAP_FIVE_ISLAND", "MAP_SIX_ISLAND", "MAP_SEVEN_ISLAND"))
    }
    for group in groups:
        version = versions[group.version_id]
        if version not in choices:
            continue
        area = areas[group.location_area_id]
        method = builder.encounters.method_identifiers[group.method_id]
        if area in notes:
            if group.pokemon_id != 201 or method != "walk":
                raise ValueError(f"{area} : rencontre de chambre de Zarbi inattendue")
            group.notes.append(notes[area])
        if area in sevii:
            group.conditions = _postgame_conditions(group, conditions)
            group.notes.append(
                "Accès aux Îles 4 à 7 avec le Passe Prisme remis par Ciléo après lui avoir apporté le Rubis."
            )
        if area.startswith("cerulean-cave/") or method.startswith("roaming"):
            group.conditions = _postgame_conditions(group, conditions)
            group.notes.append(
                "Après avoir remis le Rubis et le Saphir à Ciléo sur l'Île 1 (liaison avec Hoenn rétablie)."
            )
        if method.startswith("roaming"):
            starter = choices[version][species[group.pokemon_id]]
            # PokéAPI demande à tort une seconde Ligue ; InitRoamer est appelé dès la remise du Saphir.
            group.conditions = tuple(
                sorted(
                    (set(group.conditions) - {conditions["story-progress-beat-elite-four-round-two"]})
                    | {conditions["starter-" + starter]}
                )
            )
            group.min_level = group.max_level = 50


def _postgame_conditions(group: EncounterGroup, conditions: dict[str, int]) -> tuple[int, ...]:
    return tuple(
        sorted(
            {*group.conditions, conditions["story-progress-hall-of-fame"], conditions["story-progress-national-dex"]}
        )
    )


def _complete_roaming_methods(builder: DatabaseBuilder, groups: list[EncounterGroup], versions: set[str]) -> None:
    identifiers = {int(row["id"]): row["identifier"] for row in builder.version_rows}
    methods = {value: key for key, value in builder.encounters.method_identifiers.items()}
    present = {
        (row.version_id, row.pokemon_id, row.method_id) for row in groups if identifiers[row.version_id] in versions
    }
    # Le moteur tente aussi l'errant pendant Surf ; PokéAPI ne fournit que la marche pour ces jeux.
    for row in tuple(groups):
        if identifiers[row.version_id] not in versions or row.method_id != methods["roaming-grass"]:
            continue
        if (row.version_id, row.pokemon_id, methods["roaming-water"]) not in present:
            groups.append(replace(row, method_id=methods["roaming-water"], notes=list(row.notes)))


def _chamber_notes(repo: Gen3PretRepo) -> dict[str, str]:
    mappings = dict(read_map_areas("firered-leafgreen")["firered-leafgreen"])
    tables = {
        table.map_const: table
        for table in repo.wild_tables["firered"]
        if "TANOBY" in table.map_const and table.method == "walk"
    }
    notes = {}
    for chamber in unown_chambers(repo):
        table = tables[chamber.map_const]
        totals: dict[int, int] = defaultdict(int)
        for letter, slot in zip(chamber.letters, table.slots, strict=True):
            if slot.species != "UNOWN":
                raise ValueError(f"{table.label} : espèce autre que Zarbi")
            totals[letter] += slot.chance
        forms = ", ".join(
            f"{'ABCDEFGHIJKLMNOPQRSTUVWXYZ!?'[letter]} : {chance} %" for letter, chance in sorted(totals.items())
        )
        notes[mappings[chamber.map_const]] = (
            f"Après avoir résolu l'énigme des sept rochers de la Clé Tanoby avec Force. Formes de Zarbi : {forms}."
        )
    return notes
