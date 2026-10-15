"""Équipes, variantes des rivaux et revanches des personnages GBA."""

from __future__ import annotations

import re
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
    kanto_rivals = _kanto_rival_battles(selected)
    selected = tuple(trainer for trainer in selected if not _KANTO_RIVAL.fullmatch(trainer))
    rows = [_kanto_rival_row(maps, version, battle, teams, actor) for battle, teams in kanto_rivals.items()]
    for trainer_id in selected:
        trainer = maps.repo.trainers[version][trainer_id]
        rows.append(
            replace(
                actor,
                kind="trainer",
                appearance=None,
                trainer_class=trainer.trainer_class,
                party=_party_rows(trainer.party),
                name_fr=_trainer_name(trainer) + (" (revanche)" if _league_rematch(trainer) else ""),
                rematches=_rematches(maps, version, trainer_id),
                held_items={
                    (1, slot): item_identifier(mon.item.removeprefix("ITEM_"), {})
                    for slot, mon in enumerate(trainer.party, start=1)
                    if mon.item
                },
            )
        )
    fixed = rows[len(kanto_rivals) :]
    return rows[: len(kanto_rivals)] + [
        _with_rematch_items(maps, version, trainer_id, row) for trainer_id, row in zip(selected, fixed, strict=True)
    ]


# Combats du rival de Rouge Feu et Vert Feuille : une équipe par Pokémon de départ du rival.
_KANTO_RIVAL = re.compile(r"TRAINER_((?:RIVAL|CHAMPION)_\w+?)_(BULBASAUR|CHARMANDER|SQUIRTLE)")
# Le rival prend le Pokémon de départ qui bat celui du joueur.
_KANTO_PLAYER_STARTER = {"BULBASAUR": "squirtle", "CHARMANDER": "bulbasaur", "SQUIRTLE": "charmander"}
# Deux combats au même endroit : celui de la Route 22 avant et après les badges, et la revanche de la Ligue.
_KANTO_RIVAL_NAMES = {
    "RIVAL_ROUTE22_EARLY": "Rival (1er combat)",
    "RIVAL_ROUTE22_LATE": "Rival (2e combat)",
    "CHAMPION_REMATCH": "Rival (revanche)",
}


def _kanto_rival_battles(trainers: tuple[str, ...]) -> dict[str, dict[str, str]]:
    battles: dict[str, dict[str, str]] = {}
    for trainer in trainers:
        if match := _KANTO_RIVAL.fullmatch(trainer):
            battles.setdefault(match[1], {})[match[2]] = trainer
    return battles


def _kanto_rival_row(
    maps: Gen3GameMaps, version: str, battle: str, teams: dict[str, str], actor: ObjectRow
) -> ObjectRow:
    if set(teams) != set(_KANTO_PLAYER_STARTER):
        raise ValueError(f"{version}:{actor.key} : trois équipes du rival attendues pour {battle}")
    trainers = maps.repo.trainers[version]
    return replace(
        actor,
        kind="trainer",
        appearance=None,
        name_fr=_KANTO_RIVAL_NAMES.get(battle, "Rival"),
        variants=[
            (VariantKind.PLAYER_STARTER, _KANTO_PLAYER_STARTER[starter], _party_rows(trainers[teams[starter]].party))
            for starter in sorted(teams, key=lambda starter: _KANTO_PLAYER_STARTER[starter])
        ],
        trainer_class=trainers[teams["BULBASAUR"]].trainer_class,
    )


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


def _league_rematch(trainer: Gen3Trainer) -> bool:
    """Seconde équipe du Conseil 4 de Rouge Feu et Vert Feuille, affrontée après la mission de Ciléo."""
    return trainer.trainer_class == "TRAINER_CLASS_ELITE_FOUR" and trainer.const.endswith("_2")


# Champions d'Arène, Conseil 4 et chef Rocket de Rouge Feu et Vert Feuille, nommés comme dans Rouge et Bleu.
_KANTO_NAMES = {
    "BROCK": "Pierre",
    "MISTY": "Ondine",
    "LT. SURGE": "Major Bob",
    "ERIKA": "Érika",
    "KOGA": "Koga",
    "SABRINA": "Morgane",
    "BLAINE": "Auguste",
    "GIOVANNI": "Giovanni",
    "LORELEI": "Olga",
    "BRUNO": "Aldo",
    "AGATHA": "Agatha",
    "LANCE": "Peter",
}


def _trainer_name(trainer: Gen3Trainer) -> str:
    named = {"TRAINER_CLASS_LEADER", "TRAINER_CLASS_ELITE_FOUR", "TRAINER_CLASS_BOSS"}
    if trainer.trainer_class in named and trainer.name in _KANTO_NAMES:
        return _KANTO_NAMES[trainer.name]
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
