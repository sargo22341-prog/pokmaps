"""Personnages, équipes, objets et Pokémon fixes DS dans le modèle commun des cartes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .maps_characters import ObjectRow
from .pret_identifiers import species_identifier
from .pret_items_gen4 import ds_item_id

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .character_actors_gen4 import CharacterActor
    from .maps_export_gen4 import Gen4MapProjection
    from .pret_gen4_trainers import Gen4Trainer
    from .preview_characters_gen4 import CharacterCatalog


def character_rows(
    builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection, source: Path
) -> list[ObjectRow]:
    from .maps_berries_gen4 import berry_offers, initial_berries
    from .maps_offers_gen4 import actor_offers, scene_rows
    from .maps_underground_actors_gen4 import underground_positions

    events = {(event.header, event.event): event for event in catalog.event_trainers}
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    berries = initial_berries(projection.maps.repo)
    result = []
    underground = {
        const: underground_positions(projection.maps.repo, header)
        for const, header in projection.maps.headers.items()
        if header.map_type == 6
    }
    for actor in _display_actors(catalog):
        header = projection.maps.headers[actor.header]
        cell = (actor.x, actor.z)
        if header.map_type == 6:
            # Pierrick est une scène placée à côté du joueur, sans emplacement permanent dans le Souterrain.
            if actor.local_id not in underground[actor.header]:
                continue
            cell = underground[actor.header][actor.local_id]
        event = projection.maps.repo.events[header.events].object_events[actor.event]
        name, appearance = catalog.names.sprites[actor.graphics]
        row = ObjectRow(
            actor.header,
            "npc",
            *projection.point(actor.header, *cell, event.y),
            str(actor.graphics) if (source / "sprites" / f"{actor.graphics}.webp").is_file() else None,
            None,
            None,
            None,
            None,
            key=actor.key,
            name_fr=catalog.names.characters.get(actor.key, name),
            appearance={"person": "npc", "object": "npc_object", "pokemon": "npc_pokemon"}[appearance],
            source_cell=cell,
        )
        if trainer := events.get((header.index, actor.event)):
            _attach_team(builder, catalog, row, trainers[trainer.trainer])
        row.offers = actor_offers(builder, catalog, actor.offers)
        if actor.graphics == 100:
            row.offers += berry_offers(builder, berries, event.data[0])
            row.name_fr = "Plantation de baies"
        result.append(row)
    result += _items(builder, catalog, projection)
    result += _fixed(catalog, projection)
    from .maps_battles_gen4 import attach_script_battles, merge_story_actors

    result = merge_story_actors(result)
    attach_script_battles(builder, catalog, projection, result, source)
    result += scene_rows(builder, catalog, projection)
    return [row for row in result if row.sprite or row.item or row.pokemon or row.offers or row.kind == "trainer"]


def _display_actors(catalog: CharacterCatalog) -> list[CharacterActor]:
    items = {(catalog.headers[item.header], item.x, item.z) for item in catalog.items if item.kind == "item"}
    fixed = {
        (encounter.header, position.x, position.z)
        for encounter in catalog.fixed
        for position in encounter.positions
        if position.kind == "object"
    }
    result = []
    for actor in catalog.actors.actors:
        if actor.scene_only or (actor.script == 65535 and actor.hidden_flag and not actor.offers):
            continue
        # Les autres avatars de la Salle Union représentent les joueurs connectés, pas des PNJ du scénario.
        if actor.header.endswith("UNION_ROOM") and actor.event > 0 and not actor.offers:
            continue
        point = (actor.header, actor.x, actor.z)
        pokemon = catalog.names.sprites[actor.graphics][1] == "pokemon"
        # Les objets ramassables et Pokémon fixes ont déjà leur propre repère, avec leur fiche complète.
        if not actor.offers and ((actor.graphics == 87 and point in items) or (pokemon and point in fixed)):
            continue
        result.append(actor)
    return result


def _attach_team(builder: DatabaseBuilder, catalog: CharacterCatalog, row: ObjectRow, trainer: Gen4Trainer) -> None:
    row.kind, row.appearance = "trainer", None
    row.trainer_class = trainer.trainer_class.lower().removeprefix("trainer_class_")
    row.name_fr = catalog.names.characters.get(row.key, catalog.names.classes[trainer.trainer_class])
    row.party = _party(trainer)
    rematches = next((series.teams[1:] for series in catalog.vs_seeker.series if series.base == trainer.id), ())
    teams = {team.id: team for team in catalog.trainers}
    selected = [trainer, *(teams[number] for number in rematches if number is not None)]
    row.rematches = [_party(team) for team in selected[1:]]
    row.held_items = {
        (index, slot): _item(builder, mon.item)
        for index, team in enumerate(selected, start=1)
        for slot, mon in enumerate(team.party, start=1)
        if mon.item
    }


def _party(trainer: Gen4Trainer) -> list[tuple[str, int, tuple[str, ...]]]:
    return [
        (
            species_identifier(mon.species.removeprefix("SPECIES_")),
            mon.level,
            tuple(move.removeprefix("MOVE_").lower().replace("_", "-") for move in mon.moves),
        )
        for mon in trainer.party
    ]


def _item(builder: DatabaseBuilder, const: str) -> str:
    return next(name for name, number in builder.items.ids.items() if number == ds_item_id(builder, const))


def _items(builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection) -> list[ObjectRow]:
    return [
        ObjectRow(
            catalog.headers[item.header],
            item.kind,
            *projection.point(catalog.headers[item.header], item.x, item.z, item.y if item.kind == "item" else None),
            None,
            _item(builder, item.item),
            None,
            None,
            None,
        )
        for item in catalog.items
    ]


def _fixed(catalog: CharacterCatalog, projection: Gen4MapProjection) -> list[ObjectRow]:
    result = []
    for encounter in catalog.fixed:
        for position in encounter.positions:
            for pokemon in encounter.pokemon:
                for version in pokemon.versions or (None,):
                    result.append(
                        ObjectRow(
                            encounter.header,
                            "pokemon",
                            *projection.point(
                                encounter.header,
                                position.x,
                                position.z,
                                position.y if position.kind == "object" else None,
                            ),
                            None,
                            None,
                            species_identifier(pokemon.species.removeprefix("SPECIES_")),
                            pokemon.level,
                            None,
                            version=version,
                        )
                    )
    return result
