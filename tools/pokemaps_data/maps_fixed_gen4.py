"""Un repère par rencontre fixe, sur le Pokémon posé plutôt que sur son déclencheur."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .maps_characters import ObjectRow
from .pret_identifiers import species_identifier

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .maps_export_gen4 import Gen4MapProjection
    from .preview_characters_gen4 import CharacterCatalog


def fixed_rows(builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection) -> list[ObjectRow]:
    names = builder.api.names("pokemon_species_names", "pokemon_species_id")
    ids = {row["identifier"]: number for number, row in builder.species.items()}
    result = []
    for encounter in catalog.fixed:
        for pokemon in encounter.pokemon:
            species = species_identifier(pokemon.species.removeprefix("SPECIES_"))
            actors = [
                actor
                for actor in catalog.actors.actors
                if actor.header == encounter.header
                and not actor.scene_only
                and catalog.names.sprites[actor.graphics] == (names[ids[species]], "pokemon")
            ]
            if len(actors) > 1:
                raise ValueError(f"{encounter.header} : plusieurs positions permanentes pour {species}")
            actor = actors[0] if actors else None
            position = next((p for p in encounter.positions if p.kind == "object"), encounter.positions[0])
            cell = (actor.x, actor.z) if actor else (position.x, position.z)
            height = None if actor or position.kind != "object" else position.y
            for version in pokemon.versions or (None,):
                result.append(
                    ObjectRow(
                        encounter.header,
                        "pokemon",
                        *projection.point(encounter.header, *cell, height),
                        str(actor.graphics) if actor else None,
                        None,
                        species,
                        pokemon.level,
                        None,
                        version=version,
                        source_cell=cell,
                    )
                )
    return result


def merge_actor_poses(rows: list[ObjectRow]) -> list[ObjectRow]:
    """Les poses diurnes/nocturnes d'une même case partagent le combat et toutes les offres."""
    grouped: dict[tuple[str, str, tuple[int, int], str | None], ObjectRow] = {}
    result = []
    for row in sorted(rows, key=lambda row: row.kind != "trainer"):
        if row.sprite is None or row.source_cell is None:
            result.append(row)
            continue
        key = (row.map_const, row.sprite, row.source_cell, row.version)
        previous = grouped.get(key)
        if previous is None:
            grouped[key] = row
            result.append(row)
            continue
        if row.kind == "trainer" and (previous.party, previous.variants) != (row.party, row.variants):
            if previous.variants or row.variants:
                raise ValueError(f"{row.map_const}:{row.source_cell} : variantes incompatibles sur une même case")
            offset = 1 + len(previous.rematches)
            previous.rematches.extend([row.party, *row.rematches])
            previous.held_items.update({(team + offset, slot): item for (team, slot), item in row.held_items.items()})
        previous.offers = list(dict.fromkeys([*previous.offers, *row.offers]))
    return result
