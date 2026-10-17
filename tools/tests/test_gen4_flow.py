"""Flux des scripts DS sur des scripts réduits : développement des macros de Platine, valeurs des variables en un
point, choix du joueur rattachés aux combats, conditions et chemins qui mènent à une étape."""

from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_flow import (
    CALL,
    CALL_COMMON,
    CALL_IF,
    CHECK_FLAG,
    COMPARE_VAR,
    COPY_VAR,
    DATA,
    END,
    GOTO,
    GOTO_IF,
    PLAYER_STARTER,
    RANDOM,
    RETURN,
    SET_VALUE,
    TRAINER_BATTLE,
    PlatinumContext,
    ScriptFlow,
    Step,
    platinum_flow,
    reachable,
    read_platinum_macros,
)
from pokemaps_data.pret_gen4_flow_chains import Chains, Condition
from pokemaps_data.pret_gen4_flow_values import (
    EXTERNAL,
    STARTER_SLOT,
    UNKNOWN,
    Choices,
    CommonScripts,
    values_at,
)
from pokemaps_data.pret_gen4_scripts import MacroCall, TextScriptFile

RESULT, TRAINER, OTHER, ITEM = 0x800C, 0x8004, 0x8005, 0x8008
CHOICES = Choices(frozenset({387, 390, 393}), frozenset({0, 1}))


def flow(*rows: tuple, entries: tuple[int, ...] = (0,), name: str = "test") -> ScriptFlow:
    """Étapes numérotées dans l'ordre : (commande, arguments, destination[, arguments écrits])."""
    steps = {}
    for key, row in enumerate(rows):
        command, arguments, target, *writes = row
        following = key + 1 if key + 1 < len(rows) else None
        written = frozenset(writes[0]) if writes else frozenset()
        steps[key] = Step(key, command, tuple(arguments), target, following, f"{command} ({key})", written)
    return ScriptFlow(name, entries, steps)


def is_battle(step: Step) -> bool:
    return step.command == TRAINER_BATTLE


def test_assignments_and_copies_reach_the_battle() -> None:
    script = flow(
        (SET_VALUE, (TRAINER, 5), None),
        (COPY_VAR, (OTHER, TRAINER), None),
        (TRAINER_BATTLE, (OTHER, 0), None),
        (END, (), None),
    )
    assert script.steps[2].command == TRAINER_BATTLE
    assert values_at(script, is_battle, {OTHER}).values(2, OTHER) == {5}


def test_branch_on_the_starter_keeps_each_team_with_its_starter() -> None:
    script = flow(
        (PLAYER_STARTER, (RESULT,), None, {0}),
        (COMPARE_VAR, (RESULT, 387), None),
        (GOTO_IF, (1,), 6),
        (SET_VALUE, (RESULT, 20), None),  # la variable est réutilisée, le choix reste attaché
        (TRAINER_BATTLE, (10, 0), None),
        (END, (), None),
        (TRAINER_BATTLE, (11, 0), None),
        (END, (), None),
    )
    values = values_at(script, is_battle, set(), common=None, choices=CHOICES)
    assert values.values(4, STARTER_SLOT) == {390, 393}
    assert values.values(6, STARTER_SLOT) == {387}
    assert values.values(4, RESULT) == {20}


def test_random_choice_resolves_both_opponents_without_external_value() -> None:
    script = flow(
        (RANDOM, (0x8006, 2), None, {0}),
        (COMPARE_VAR, (0x8006, 0), None),
        (CALL_IF, (1,), 8),
        (COMPARE_VAR, (0x8006, 1), None),
        (CALL_IF, (1,), 10),
        (TRAINER_BATTLE, (0x8007, 0), None),
        (END, (), None),
        (END, (), None),
        (SET_VALUE, (0x8007, 892), None),
        (RETURN, (), None),
        (SET_VALUE, (0x8007, 893), None),
        (RETURN, (), None),
    )
    assert values_at(script, is_battle, {0x8007}).values(5, 0x8007) == {892, 893}


def test_unknown_writes_and_external_values_stay_visible() -> None:
    script = flow(("ScrCmd_Write", (TRAINER,), None, {0}), (TRAINER_BATTLE, (TRAINER, OTHER), None), (END, (), None))
    values = values_at(script, is_battle, {TRAINER, OTHER})
    assert values.values(1, TRAINER) == {UNKNOWN}
    assert values.values(1, OTHER) == {EXTERNAL}


def test_common_scripts_only_forget_the_variables_they_write() -> None:
    common = CommonScripts(flow((SET_VALUE, (TRAINER, 1), None), (RETURN, (), None)), 2000)
    script = flow(
        (SET_VALUE, (TRAINER, 5), None),
        (SET_VALUE, (ITEM, 6), None),
        (CALL_COMMON, (2000,), None),
        (TRAINER_BATTLE, (ITEM, TRAINER), None),
        (END, (), None),
    )
    values = values_at(script, is_battle, {TRAINER, ITEM}, common=common)
    assert values.values(3, ITEM) == {6}
    assert values.values(3, TRAINER) == {UNKNOWN}
    # Sans le fichier des scripts communs, toutes les variables locales sont perdues.
    assert values_at(script, is_battle, {TRAINER, ITEM}).values(3, ITEM) == {UNKNOWN}


def test_recursive_calls_and_unknown_conditions_stop_the_reading() -> None:
    with pytest.raises(ValueError, match="récursifs"):
        values_at(flow((CALL, (), 0), (END, (), None)), is_battle, set())
    script = flow((COMPARE_VAR, (RESULT, 1), None), (GOTO_IF, (9,), 3), (END, (), None), (END, (), None))
    with pytest.raises(ValueError, match="condition de saut inconnue"):
        values_at(script, is_battle, {RESULT})


def test_conditions_and_paths_follow_the_script_order() -> None:
    script = flow(
        (CHECK_FLAG, (272,), None),
        (GOTO_IF, (0,), 5),  # drapeau non défini : saut
        (COMPARE_VAR, (RESULT, 1), None),
        (GOTO_IF, (1,), 6),
        (END, (), None),
        (GOTO, (), 6),
        ("national_dex", (1, RESULT), None),
        (END, (), None),
        entries=(0,),
    )
    chains = Chains(script)
    assert chains.paths(6) == (
        (Condition("flag:272", "=", 0),),
        (Condition("flag:272", "=", 1), Condition("var:32780", "=", 1)),
    )
    assert chains.conditions(4) == (Condition("flag:272", "=", 1), Condition("var:32780", "!=", 1))
    assert reachable(script, 0) == set(range(8))


def _macros(root: Path) -> None:
    (root / "asm/macros").mkdir(parents=True)
    (root / "asm/macros/scrcmd.inc").write_text(
        "\n".join(
            [
                ".macro End\n.short 2\n.endm",
                ".macro GoTo offset\n.short 22\n.endm",
                ".macro GoToIf condition, offset\n.short 28\n.endm",
                ".macro CompareVar varID, valueOrVarID\n.short 17\n.endm",
                ".macro GoToIfEq varID, valueOrVarID, offset\n"
                "CompareVar \\varID, \\valueOrVarID\nGoToIf 1, \\offset\n.endm",
                ".macro SetVarFromValue destVarID, value\n.short 40\n.endm",
                ".macro SetVarFromVar destVarID, srcVarID\n.short 41\n.endm",
                ".macro StartTrainerBattle enemyTrainer1, enemyTrainer2=0\n.short 229\n.endm",
                ".macro ShowYesNoMenu destVarID\n.short 62\n.endm",
                ".macro CallCommonScript scriptID\n.short 20\n.endm",
                ".macro Common_Check\nCallCommonScript 0x7D1\n.endm",
            ]
        ),
        encoding="utf-8",
    )
    (root / "asm/macros/movement.inc").write_text(".macro WalkNorth count\n.short 1\n.endm\n", encoding="utf-8")


def test_platinum_macros_expand_like_the_assembler(tmp_path: Path) -> None:
    _macros(tmp_path)
    templates, writes = read_platinum_macros(tmp_path)
    assert writes["ShowYesNoMenu"] == {0} and writes["StartTrainerBattle"] == frozenset()
    constants = {"TRAINER_A": 7, "VAR_RESULT": RESULT, "VAR_0x8004": TRAINER}
    calls = {
        "Start": (
            MacroCall(1, "SetVar", ("VAR_RESULT", "TRAINER_A")),
            MacroCall(2, "SetVar", ("VAR_0x8004", "VAR_RESULT")),
            MacroCall(3, "Common_Check", ()),
            MacroCall(4, "GoToIfEq", ("VAR_RESULT", "LOCAL", "Battle")),
        ),
        "Battle": (MacroCall(6, "StartTrainerBattle", ("TRAINER_A",)), MacroCall(7, "End", ())),
        "Movement": (MacroCall(9, "WalkNorth", ("1",)),),
    }
    script = TextScriptFile("scripts_test", ("Start",), {"LOCAL": "3"}, (), calls)
    built = platinum_flow(script, PlatinumContext(templates, writes, frozenset({"WalkNorth"}), constants))
    commands = [step.command for step in built.steps.values()]
    assert commands == [SET_VALUE, COPY_VAR, CALL_COMMON, COMPARE_VAR, GOTO_IF, TRAINER_BATTLE, END, DATA]
    assert built.steps["Start", 3].arguments == (RESULT, 3)
    assert built.steps["Start", 4].target == ("Battle", 5)
    # Le dernier appel d'un label continue au label suivant, et l'argument omis prend sa valeur par défaut.
    assert built.steps["Start", 4].following == ("Battle", 5)
    assert built.steps["Battle", 5].arguments == (7, 0)
    with pytest.raises(ValueError, match="données"):
        built.step(("Movement", 7))
