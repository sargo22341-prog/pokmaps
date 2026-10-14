"""Équipes, variantes de Flora et revanches des personnages GBA."""

from __future__ import annotations

from dataclasses import replace

from .maps_characters import ObjectRow
from .maps_characters_data import read_character_names
from .maps_layout_gen3 import Gen3GameMaps
from .pret_gen3_trainers import Gen3Trainer, Gen3TrainerPokemon
from .pret_identifiers import item_identifier, species_identifier
from .pret_models import VariantKind


def trainer_rows(
    maps: Gen3GameMaps,
    version: str,
    trainers: tuple[str, ...],
    actor: ObjectRow,
) -> list[ObjectRow]:
    rival = any(trainer.startswith("TRAINER_MAY_") for trainer in trainers)
    selected = tuple(trainer for trainer in trainers if trainer.startswith("TRAINER_MAY_")) if rival else trainers
    if rival:
        return [_rival_row(maps, version, selected, actor)]
    rows = []
    for trainer_id in selected:
        trainer = maps.repo.trainers[version][trainer_id]
        rows.append(
            replace(
                actor,
                kind="trainer",
                appearance=None,
                trainer_class=trainer.trainer_class,
                party=_party_rows(trainer.party),
                name_fr=_trainer_name(trainer),
                rematches=_rematches(maps, version, trainer_id),
                held_items={
                    (1, slot): item_identifier(mon.item.removeprefix("ITEM_"), {})
                    for slot, mon in enumerate(trainer.party, start=1)
                    if mon.item
                },
            )
        )
    return [_with_rematch_items(maps, version, trainer_id, row) for trainer_id, row in zip(selected, rows, strict=True)]


def _rival_row(maps: Gen3GameMaps, version: str, trainers: tuple[str, ...], actor: ObjectRow) -> ObjectRow:
    starters = {"TREECKO": "treecko", "TORCHIC": "torchic", "MUDKIP": "mudkip"}
    variants = [
        (
            VariantKind.PLAYER_STARTER,
            _player_starter(maps.repo.trainers[version][trainer]),
            _party_rows(maps.repo.trainers[version][trainer].party),
        )
        for trainer in trainers
    ]
    if len(variants) != 3 or {pokemon for _, pokemon, _ in variants} != set(starters.values()):
        raise ValueError(f"{version}:{actor.key} : trois variantes de Flora attendues")
    return replace(
        actor,
        kind="trainer",
        appearance=None,
        name_fr="Flora",
        variants=variants,
        trainer_class=maps.repo.trainers[version][trainers[0]].trainer_class,
    )


def _player_starter(trainer: Gen3Trainer) -> str:
    rivals = {
        "treecko": {"SPECIES_TORCHIC", "SPECIES_COMBUSKEN", "SPECIES_BLAZIKEN"},
        "torchic": {"SPECIES_MUDKIP", "SPECIES_MARSHTOMP", "SPECIES_SWAMPERT"},
        "mudkip": {"SPECIES_TREECKO", "SPECIES_GROVYLE", "SPECIES_SCEPTILE"},
    }
    choices = [player for player, family in rivals.items() if any(mon.species in family for mon in trainer.party)]
    if len(choices) != 1:
        raise ValueError(f"{trainer.const} : partenaire de la rivale absent ou ambigu")
    return choices[0]


def _rematch_ids(maps: Gen3GameMaps, version: str, trainer: str) -> tuple[str, ...]:
    series = next((row for row in maps.repo.rematches[version] if row.teams[0].trainer == trainer), None)
    return tuple(team.trainer for team in series.teams[1:]) if series else ()


def _rematches(maps: Gen3GameMaps, version: str, trainer: str) -> list[list[tuple[str, int, tuple[str, ...]]]]:
    return [_party_rows(maps.repo.trainers[version][key].party) for key in _rematch_ids(maps, version, trainer)]


def _with_rematch_items(maps: Gen3GameMaps, version: str, trainer: str, row: ObjectRow) -> ObjectRow:
    held = dict(row.held_items)
    for team, key in enumerate(_rematch_ids(maps, version, trainer), 2):
        for slot, mon in enumerate(maps.repo.trainers[version][key].party, 1):
            if mon.item:
                held[team, slot] = item_identifier(mon.item.removeprefix("ITEM_"), {})
    return replace(row, held_items=held)


def _trainer_name(trainer: Gen3Trainer) -> str:
    if trainer.name == "WALLY":
        return "Timmy"
    if trainer.name == "STEVEN":
        return "Pierre Rochard"
    if trainer.name == "WALLACE":
        return "Marc"
    if trainer.const.startswith("TRAINER_TATE_AND_LIZA"):
        return "Lévy et Tatia"
    names = {
        "ARCHIE": "Arthur",
        "MAXIE": "Max",
        "MATT": "Matthieu",
        "SHELLY": "Sarah",
        "TABITHA": "Kelvin",
        "COURTNEY": "Courtney",
    }
    if trainer.trainer_class in {
        "TRAINER_CLASS_AQUA_ADMIN",
        "TRAINER_CLASS_AQUA_LEADER",
        "TRAINER_CLASS_MAGMA_ADMIN",
        "TRAINER_CLASS_MAGMA_LEADER",
    }:
        if trainer.name not in names:
            raise ValueError(f"{trainer.const} : nom français du chef ou de l'admin absent : {trainer.name}")
        return names[trainer.name]
    return read_character_names().trainer(trainer.trainer_class)


def _party_rows(party: tuple[Gen3TrainerPokemon, ...]) -> list[tuple[str, int, tuple[str, ...]]]:
    return [
        (
            species_identifier(mon.species.removeprefix("SPECIES_")),
            mon.level,
            tuple(move.removeprefix("MOVE_").lower().replace("_", "-") for move in mon.moves),
        )
        for mon in party
    ]
