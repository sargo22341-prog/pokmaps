"""Rencontres fixes GBA : quantités et versions attestées par les événements pret."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from .games import PretFormat
from .maps import read_map_areas
from .pret_gen3_fixed import fixed_encounters
from .pret_identifiers import species_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .builder_encounters import EncounterGroup


def reconcile_fixed_encounters(builder: DatabaseBuilder, groups: list[EncounterGroup]) -> None:
    methods = {name: key for key, name in builder.encounters.method_identifiers.items()}
    species = {row["identifier"]: key for key, row in builder.species.items()}
    versions = {row["identifier"]: int(row["id"]) for row in builder.version_rows}
    for game in builder.games:
        if game.pret_format is not PretFormat.GEN3:
            continue
        repo = builder.gen3_repo(game, "les Pokémon fixes")
        mappings = dict(read_map_areas(game.version_group)[game.map_family])
        for version, _ in game.pret_versions:
            rows = fixed_encounters(repo, version)
            by_method: dict[int, Counter[tuple[int, int, int]]] = defaultdict(Counter)
            seen: set[tuple] = set()
            for row in rows:
                current = next(current for current in repo.maps.values() if current.label == row["map"])
                if current.const not in mappings:
                    continue
                area = builder.locations.area_ids[mappings[current.const]]
                mon = species[species_identifier(str(row["pokemon"]).removeprefix("SPECIES_"))]
                identity = (current.const, row["x"], row["y"], mon, row["level"])
                if identity in seen:
                    continue  # Plusieurs chemins du script ne créent pas plusieurs Pokémon sur une case.
                seen.add(identity)
                method = methods[
                    {species["kecleon"]: "devon-scope", species["snorlax"]: "pokeflute"}.get(mon, "static")
                ]
                by_method[method][area, mon, int(row["level"])] += 1
            for method, expected in sorted(by_method.items()):
                balls = {species["voltorb"], species["electrode"]} if method == methods["static"] else set()
                _replace_groups(groups, versions[version], method, expected, balls)


def _replace_groups(
    groups: list[EncounterGroup],
    version: int,
    method: int,
    expected: Counter[tuple[int, int, int]],
    balls: set[int],
) -> None:
    from .builder_encounters import EncounterGroup

    keys = {(area, mon) for area, mon, _ in expected}
    originals = {
        (g.location_area_id, g.pokemon_id): g for g in groups if g.version_id == version and g.method_id == method
    }
    groups[:] = [
        g
        for g in groups
        if not (
            g.version_id == version
            and g.method_id == method
            and ((g.location_area_id, g.pokemon_id) in keys or g.pokemon_id in balls)
        )
    ]
    for (area, mon, level), quantity in sorted(expected.items()):
        original = originals.get((area, mon))
        groups.append(
            EncounterGroup(
                version,
                area,
                mon,
                method,
                original.conditions if original else (),
                level,
                level,
                None,
                quantity,
                list(original.notes) if original else [],
            )
        )
