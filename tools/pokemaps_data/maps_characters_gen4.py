"""Personnages, équipes, objets et Pokémon fixes DS dans le modèle commun des cartes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .maps_characters import ObjectRow
from .pret_identifiers import species_identifier
from .pret_items_gen4 import ds_item_id
from .pret_models import VariantKind

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .maps_export_gen4 import Gen4MapProjection
    from .pret_gen4_trainers import Gen4Trainer
    from .preview_characters_gen4 import CharacterCatalog


def character_rows(
    builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection, source: Path
) -> list[ObjectRow]:
    from .maps_offers_gen4 import actor_offers, scene_rows

    events = {(event.header, event.event): event for event in catalog.event_trainers}
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    result = []
    for actor in catalog.actors.actors:
        if actor.scene_only:
            continue
        header = projection.maps.headers[actor.header]
        event = projection.maps.repo.events[header.events].object_events[actor.event]
        name, appearance = catalog.names.sprites[actor.graphics]
        row = ObjectRow(
            actor.header,
            "npc",
            *projection.point(actor.header, actor.x, actor.z, event.y),
            str(actor.graphics) if (source / "sprites" / f"{actor.graphics}.webp").is_file() else None,
            None,
            None,
            None,
            None,
            key=actor.key,
            name_fr=catalog.names.characters.get(actor.key, name),
            appearance={"person": "npc", "object": "npc_object", "pokemon": "npc_pokemon"}[appearance],
            source_cell=(actor.x, actor.z),
        )
        if trainer := events.get((header.index, actor.event)):
            _attach_team(builder, catalog, row, trainers[trainer.trainer])
        row.offers = actor_offers(builder, catalog, actor.offers)
        result.append(row)
    result += _items(builder, catalog, projection)
    result += _fixed(catalog, projection)
    result += _battles(builder, catalog, projection)
    result += scene_rows(builder, catalog, projection)
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


def _battles(builder: DatabaseBuilder, catalog: CharacterCatalog, projection: Gen4MapProjection) -> list[ObjectRow]:
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    result = []
    for battle in catalog.script_battles:
        for const in catalog.script_headers[battle.script_file]:
            # Une scène n'a pas nécessairement de PNJ posé : son entrée appartient au lieu entier.
            region = projection.maps.by_const[const]
            x, y = region.x + region.width // 2, region.y + region.height // 2
            for slot in range(max(len(variant.opponents) for variant in battle.variants)):
                variants = list(
                    dict.fromkeys(
                        (variant.opponents[slot], variant.player_starter)
                        for variant in battle.variants
                        if slot < len(variant.opponents)
                    )
                )
                row = ObjectRow(const, "trainer", x, y, None, None, None, None, None)
                _attach_team(builder, catalog, row, trainers[variants[0][0]])
                if len(variants) > 1 and all(starter for _, starter in variants):
                    row.party, row.rematches = [], []
                    row.variants = [
                        (VariantKind.PLAYER_STARTER, builder.species[starter]["identifier"], _party(trainers[number]))
                        for number, starter in variants
                    ]
                    row.held_items = {
                        (team, slot): _item(builder, mon.item)
                        for team, (number, _) in enumerate(variants, start=1)
                        for slot, mon in enumerate(trainers[number].party, start=1)
                        if mon.item
                    }
                    result.append(row)
                else:
                    for number, _ in variants:
                        alternate = ObjectRow(const, "trainer", x, y, None, None, None, None, None)
                        _attach_team(builder, catalog, alternate, trainers[number])
                        result.append(alternate)
    return result
