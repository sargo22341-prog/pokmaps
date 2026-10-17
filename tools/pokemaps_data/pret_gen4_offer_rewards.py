"""Valeurs des récompenses conservées entre visites et des cadeaux du Square Paisible.

Les variables persistantes ne sont pas des entrées arbitraires : leur domaine est fixé par les
scripts qui les alimentent. On conserve les possibilités, sans prédire le tirage de la partie.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import c_initializer
from .pret_gen4_flow import COPY_VAR, SET_VALUE, Key, ScriptFlow
from .pret_gen4_source import read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo


def reward_initial(repo: Gen4PretRepo, flow: ScriptFlow) -> tuple[tuple[int, tuple[int, ...]], ...]:
    if flow.name in {"scripts_route_221_house", "scripts 445"}:
        var = repo.constants["VAR_ROUTE_221_HOUSE_REWARD_INDEX"] if repo.platinum else 16648
        return ((var, (0, 1, 2)),)
    if flow.name in {"scripts_solaceon_town_pokemon_news_press", "scripts 1009"}:
        var = repo.constants["VAR_POKEMON_NEWS_PRESS_POKE_BALL_REWARD"] if repo.platinum else 16663
        rewards = tuple(
            sorted(
                {
                    int(step.arguments[1])
                    for step in flow.steps.values()
                    if step.command == SET_VALUE
                    and step.arguments[0] == 0x8004
                    and isinstance(step.arguments[1], int)
                    and 1 <= step.arguments[1] <= 16
                }
            )
        )
        if len(rewards) != 12:
            raise ValueError(f"{flow.name} : douze Balls de récompense attendues : {rewards}")
        return ((var, rewards),)
    if flow.name == "scripts_amity_square":
        var = repo.constants["VAR_FOLLOWER_MON_PICKUP_ITEM_ID"]
        berries = tuple(
            sorted(
                {
                    int(step.arguments[1])
                    for step in flow.steps.values()
                    if step.command == SET_VALUE and step.arguments[0] == var
                }
            )
        )
        if len(berries) != 9:
            raise ValueError("Square Paisible : neuf baies de ramassage attendues")
        return ((var, berries),)
    return ()


def reward_outputs(repo: Gen4PretRepo, flow: ScriptFlow) -> tuple[tuple[Key, tuple[tuple[int, int], ...]], ...]:
    if flow.name != "scripts_amity_square":
        return ()
    text = read_text(repo.root / "src/scrcmd_amity_square.c")
    table = c_initializer(text, "sBerryAndAccessoryManOptions", "scrcmd_amity_square.c")
    berries = re.findall(r"\bITEM_\w+", table)
    if len(berries) != 9:
        raise ValueError("Square Paisible : table des neuf baies donnée par le monsieur modifiée")
    outputs = []
    for step in flow.steps.values():
        if step.command == "GetAmitySquareBerryOrAccessoryIDFromMan":
            outputs += [(step.key, ((int(step.arguments[1]), repo.constants[item]),)) for item in berries]
        # La variable du ramassage garde sa valeur entre visites ; les commandes de préparation
        # peuvent la récrire en passant par une autre variable locale.
        elif step.command == COPY_VAR and step.arguments[0] == repo.constants["VAR_FOLLOWER_MON_PICKUP_ITEM_ID"]:
            outputs += [
                (step.key, ((int(step.arguments[0]), value),))
                for _, values in reward_initial(repo, flow)
                for value in values
            ]
    return tuple(outputs)


def scratch_rewards(repo: Gen4PretRepo) -> tuple[tuple[str, int], ...]:
    relative = "src/applications/scratch_off_cards/main.c"
    text = read_text(repo.root / relative)
    table = c_initializer(text, "sAvailableItems", relative)
    berries = re.findall(r"\bITEM_\w+", table)
    if len(berries) != 23 or "app->wonItemsCount[app->currentCard] = 3;" not in text:
        raise ValueError(f"{relative} : récompenses des cartes à gratter modifiées")
    if "app->wonItemsCount[app->currentCard] = 1;" not in text or "ITEM_NUGGET" not in text:
        raise ValueError(f"{relative} : récompense Pépite modifiée")
    return (("ITEM_NUGGET", 1), *((item, 3) for item in berries))
