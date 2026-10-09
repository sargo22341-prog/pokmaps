"""Catalogue des équipes et revanches GBA exporté dans l'aperçu, avec liens aux événements."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .maps_layout_gen3 import Gen3GameMaps
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_rematches import TrainerRematches
from .pret_gen3_trainers import Gen3Trainer
from .sources import PRET_COMMITS


@dataclass(frozen=True)
class TrainerBinding:
    map_const: str
    map_label: str
    local_id: str
    script: str
    x: int
    y: int
    elevation: int
    graphics: str
    removal_flag: str
    world_position: tuple[int, int] | None
    trainers: tuple[str, ...]


@dataclass(frozen=True)
class TrainerCatalog:
    version_group: str
    version: str
    repo: str
    commit: str
    trainers: tuple[Gen3Trainer, ...]
    rematches: tuple[TrainerRematches, ...]
    bindings: tuple[TrainerBinding, ...]


def trainer_catalogs(maps: Gen3GameMaps) -> tuple[TrainerCatalog, ...]:
    repo, game = maps.repo, maps.game
    result = []
    for version, _ in game.pret_versions:
        bindings = []
        for current in sorted(repo.maps.values(), key=lambda current: current.number):
            for index, event in enumerate(current.objects, 1):
                label = str(event.value("script"))
                trainers = repo.offers[version].read(label).trainers
                if trainers:
                    bindings.append(_binding(maps, current, event, index, trainers))
        catalog = TrainerCatalog(
            game.version_group,
            version,
            game.pret_repo,
            PRET_COMMITS[game.pret_repo],
            tuple(repo.trainers[version].values()),
            repo.rematches[version],
            tuple(bindings),
        )
        validate_trainer_catalog(catalog)
        result.append(catalog)
    return tuple(result)


def _binding(
    maps: Gen3GameMaps, current: Gen3Map, event: Gen3Event, index: int, trainers: tuple[str, ...]
) -> TrainerBinding:
    position = maps.point(current.const, event.x, event.y) if current.const in maps.placements else None
    return TrainerBinding(
        current.const,
        current.label,
        str(dict(event.fields).get("local_id", index)),
        str(event.value("script")),
        event.x,
        event.y,
        event.elevation,
        str(event.value("graphics_id")),
        str(event.value("flag")),
        position,
        trainers,
    )


def validate_trainer_catalog(catalog: TrainerCatalog) -> None:
    trainers = {trainer.const: trainer for trainer in catalog.trainers}
    if not trainers or len(trainers) != len(catalog.trainers):
        raise ValueError(f"{catalog.version} : catalogue de dresseurs vide ou répété")
    for trainer in catalog.trainers:
        if not 1 <= len(trainer.party) <= 6 or type(trainer.double_battle) is not bool:
            raise ValueError(f"{trainer.const} : équipe ou type de combat invalide")
        for mon in trainer.party:
            if not 1 <= mon.level <= 100 or not 0 <= mon.iv <= 255 or len(mon.move_slots) != 4 or not mon.moves:
                raise ValueError(f"{trainer.const} : Pokémon de dresseur invalide : {mon}")
    bases = [row.teams[0].trainer for row in catalog.rematches if row.teams]
    if len(bases) != len(catalog.rematches) or len(set(bases)) != len(bases):
        raise ValueError(f"{catalog.version} : série de revanches vide ou répétée")
    for row in catalog.rematches:
        _validate_rematches(row, trainers)
    for binding in catalog.bindings:
        if not binding.trainers or set(binding.trainers) - trainers.keys():
            raise ValueError(f"{binding.script} : dresseur lié absent du catalogue")
    keys = [(binding.map_const, binding.local_id) for binding in catalog.bindings]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{catalog.version} : événement de dresseur répété")


def _validate_rematches(row: TrainerRematches, trainers: dict[str, Gen3Trainer]) -> None:
    stages = tuple(team.stage for team in row.teams)
    if stages[0] != 0 or stages != tuple(sorted(set(stages))):
        raise ValueError(f"{row.map_const} : rangs de revanche invalides : {stages}")
    prior = []
    for team in row.teams:
        if team.trainer not in trainers or any(trainer not in trainers for trainer in team.previous_trainers):
            raise ValueError(f"{row.map_const} : équipe de revanche absente : {team.trainer}")
        if team.stage and not team.conditions:
            raise ValueError(f"{row.map_const} : revanche sans condition : {team.trainer}")
        if team.previous_trainers != tuple(dict.fromkeys(prior)):
            raise ValueError(f"{row.map_const} : progression de revanche incohérente : {team.trainer}")
        prior.append(team.trainer)


def write_trainer_catalogs(output: Path, catalogs: list[TrainerCatalog]) -> None:
    versions = [catalog.version for catalog in catalogs]
    if not versions or len(set(versions)) != len(versions):
        raise ValueError("Catalogue de dresseurs : versions vides ou répétées")
    for catalog in catalogs:
        validate_trainer_catalog(catalog)
    payload = {"schema": 1, "versions": [asdict(catalog) for catalog in catalogs]}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
