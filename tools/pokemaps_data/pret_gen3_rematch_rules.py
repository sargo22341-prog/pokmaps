"""Vérification des règles de revanche Hoenn contre les fonctions du moteur épinglé."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_gen3_source import balanced_bodies, read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


def _function(text: str, name: str) -> str:
    pattern = r"(?m)^(?:static\s+)?\w+\s+(" + re.escape(name) + r")\([^;{}]*\)\s*\{"
    bodies = balanced_bodies(text, pattern, 1)
    return bodies[0][1]


def _require(body: str, pattern: str, where: str) -> None:
    if not re.search(pattern, body, re.S):
        raise ValueError(f"{where} : règles de revanche du moteur modifiées ({pattern})")


def validate_hoenn_rules(repo: Gen3PretRepo) -> None:
    text = read_text(repo.root / "src/battle_setup.c")
    badges = r"badgeCount\s*>=\s*5" if repo.ruby else r"\+\+count\s*>=\s*5"
    _require(_function(text, "HasAtLeastFiveBadges"), badges, "Badges Hoenn")
    maximum = "TRAINER_REMATCH_STEPS" if repo.ruby else "STEP_COUNTER_MAX"
    constants = read_text(repo.root / "include/battle_setup.h") if repo.ruby else text
    _require(constants, r"#define\s+" + maximum + r"\s+255\b", "Pas Hoenn")
    counter = "IsRematchStepCounterMaxed"
    _require(_function(text, counter), r"HasAtLeastFiveBadges\(\).*?>=\s*" + maximum, counter)
    update = "UpdateRandomTrainerEyeRematches" if repo.ruby else "UpdateRandomTrainerRematches"
    _require(_function(text, update), r"Random\(\)\s*%\s*100\)\s*<=\s*30", update)
    if not repo.ruby:
        _emerald_rules(repo, text)


def _emerald_rules(repo: Gen3PretRepo, text: str) -> None:
    for name, stat, interval in (
        ("TryUpdateGymLeaderRematchFromWild", "WILD", 60),
        ("TryUpdateGymLeaderRematchFromTrainer", "TRAINER", 20),
    ):
        pattern = rf"GetGameStat\(GAME_STAT_{stat}_BATTLES\)\s*%\s*{interval}\s*==\s*0"
        _require(_function(text, name), pattern, name)
    gym = read_text(repo.root / "src/gym_leader_rematch.c")
    body = _function(gym, "UpdateGymLeaderRematch")
    _require(body, r"FlagGet\(FLAG_SYS_GAME_CLEAR\).*?Random\(\)\s*%\s*100\)\s*<=\s*30", "Champions")
    _require(body, r"FlagGet\(FLAG_WATTSON_REMATCH_AVAILABLE\)", "New Lavandia")
    for period, maximum in (("After", 5), ("Before", 1)):
        _require(body, rf"GymLeaderRematches_{period}NewMauville\),\s*{maximum}\)", "Rangs des Champions")
    call = read_text(repo.root / "src/match_call.c")
    _require(_function(call, "ShouldTrainerRequestBattle"), r"GetNumOwnedBadges\(\)\s*<\s*5", "Appels")
    _require(
        _function(call, "SelectMatchCallMessage"), r"ShouldTrainerRequestBattle.*?UpdateRematchIfDefeated", "Appels"
    )
