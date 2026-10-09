"""Tables de revanches GBA, rangs conservés et conditions du moteur."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo
    from .pret_gen3_trainers import Gen3Trainer

_FRLG_FLAGS = (
    "FLAG_GOT_VS_SEEKER",
    "FLAG_WORLD_MAP_CELADON_CITY",
    "FLAG_WORLD_MAP_FUCHSIA_CITY",
    "FLAG_SYS_GAME_CLEAR",
    "FLAG_SYS_CAN_LINK_WITH_RS",
)
_FRLG_PHRASES = (
    "Après l'obtention du Cherche VS",
    "Après la première visite à Céladopole",
    "Après la première visite à Parmanie",
    "Après la Ligue",
    "Après la remise du Saphir à Ciléo",
)


@dataclass(frozen=True)
class RematchTeam:
    trainer: str
    stage: int
    flags: tuple[str, ...]
    conditions: tuple[str, ...]


@dataclass(frozen=True)
class TrainerRematches:
    map_const: str
    teams: tuple[RematchTeam, ...]


def read_rematches(repo: Gen3PretRepo, version: str, trainers: dict[str, Gen3Trainer]) -> tuple[TrainerRematches, ...]:
    path = "src/vs_seeker.c" if repo.remake else "src/battle_setup.c"
    text = _remake_text(repo) if repo.remake else repo.source_text(path, version)
    if repo.remake:
        rows = re.findall(r"\{\s*\{([^{}]+)\},\s*MAP\((MAP_\w+)\)\s*\}", text)
        _validate_remake_conditions(text)
    elif repo.ruby:
        rows = re.findall(r"\{\s*\{([^{}]+)\},\s*MAP_GROUP\((MAP_\w+)\),\s*MAP_NUM\(\2\),\s*\}", text)
    else:
        rows = [(parties, const) for parties, const in re.findall(r"= REMATCH\(([^()]+),\s*(MAP_\w+)\)", text)]
    if not 1 <= len(rows) <= 1024:
        raise ValueError(f"{repo.root} : table de revanches absente ou trop grande")
    result = []
    for parties, const in rows:
        slots = tuple(value.strip() for value in parties.split(","))
        if "TRAINER_NONE" in slots:
            end = slots.index("TRAINER_NONE")
            if any(value != "TRAINER_NONE" for value in slots[end:]):
                raise ValueError(f"{const} : équipe après la fin des revanches")
            slots = slots[:end]
        maximum = 6 if repo.remake else 5
        if not 2 <= len(slots) <= maximum or any(value not in trainers and value != "SKIP" for value in slots):
            raise ValueError(f"{const} : équipes de revanche invalides : {slots}")
        teams = tuple(_team(repo, trainer, stage) for stage, trainer in enumerate(slots) if trainer != "SKIP")
        result.append(TrainerRematches(const, teams))
    if len({row.teams[0].trainer for row in result}) != len(result):
        raise ValueError(f"{repo.root} : dresseur répété dans les revanches")
    return tuple(result)


def _remake_text(repo: Gen3PretRepo) -> str:
    # Le branchement C23 de la routine d'animation n'affecte ni la table ni ses conditions.
    text = read_text(repo.root / "src/vs_seeker.c")
    table = re.search(r"static const struct RematchData sRematches\[\]\s*=\s*\{(.*?)\n\};", text, re.S)
    gates = re.search(r"static void TryGetRematchTrainerIdGivenGameState\([^)]*\)\s*\{(.*?)\n\}", text, re.S)
    if not table or not gates or "#" in table[0] + gates[0]:
        raise ValueError("Cherche VS : table ou conditions absentes ou conditionnelles")
    return table[0] + "\n" + gates[0]


def _validate_remake_conditions(text: str) -> None:
    body = re.search(r"static void TryGetRematchTrainerIdGivenGameState\([^)]*\)\s*\{(.*?)\n\}", text, re.S)
    if not body:
        raise ValueError("Cherche VS : fonction des conditions absente")
    gates = re.findall(r"case (\d+):\s*if \(!FlagGet\((FLAG_\w+)\)\)", body[1])
    if gates != [(str(stage), flag) for stage, flag in enumerate(_FRLG_FLAGS, start=1)]:
        raise ValueError(f"Cherche VS : conditions du moteur modifiées : {gates}")


def _team(repo: Gen3PretRepo, trainer: str, stage: int) -> RematchTeam:
    if stage == 0:
        return RematchTeam(trainer, stage, (), ())
    if repo.remake:
        return RematchTeam(trainer, stage, (_FRLG_FLAGS[stage - 1],), (_FRLG_PHRASES[stage - 1], "Cherche VS chargé"))
    if not repo.ruby and trainer.startswith(
        ("TRAINER_SIDNEY", "TRAINER_PHOEBE", "TRAINER_GLACIA", "TRAINER_DRAKE", "TRAINER_WALLACE")
    ):
        return RematchTeam(trainer, stage, (), ("Nouvelle participation à la Ligue, sans changement d'équipe",))
    leader = not repo.ruby and trainer.startswith(
        (
            "TRAINER_ROXANNE_",
            "TRAINER_BRAWLY_",
            "TRAINER_WATTSON_",
            "TRAINER_FLANNERY_",
            "TRAINER_NORMAN_",
            "TRAINER_WINONA_",
            "TRAINER_TATE_AND_LIZA_",
            "TRAINER_JUAN_",
        )
    )
    if leader:
        flags = ("FLAG_SYS_GAME_CLEAR",)
        if stage >= 2 or trainer.startswith("TRAINER_WATTSON_"):
            flags += ("FLAG_WATTSON_REMATCH_AVAILABLE",)
        phrases = (
            "Après la Ligue",
            "Appel de revanche du Champion, après 20 combats de dresseurs ou 60 combats sauvages",
        )
        if "FLAG_WATTSON_REMATCH_AVAILABLE" in flags:
            phrases += ("Après la quête de New Lavandia",)
    else:
        flags = ("FLAG_DEFEATED_WALLY_VICTORY_ROAD",) if trainer.startswith("TRAINER_WALLY_VR_") else ()
        phrases = ("Au moins cinq badges, après 255 pas, lorsque le dresseur propose une revanche",)
    if stage > 1:
        phrases += ("Après la victoire contre l'équipe précédente",)
    return RematchTeam(trainer, stage, flags, phrases)
