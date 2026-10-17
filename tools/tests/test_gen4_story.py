"""Étapes du scénario DS : lignes de story_events.csv des dépôts DS et traduction des conditions des chemins."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemaps_data import story_events
from pokemaps_data.pret_gen4_flow_chains import Condition
from pokemaps_data.story_conditions_gen4 import ScenarioConditions
from pokemaps_data.story_events import DS_REPOS, read_story_events

_HEADER = "repos,flag,when_set,when_clear,reason,operator,value,phrase\n"


def _story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rows: str) -> story_events.StoryEvents:
    (tmp_path / "story_events.csv").write_text(_HEADER + rows, encoding="utf-8")
    monkeypatch.setattr(story_events, "DATA_DIR", tmp_path)
    return read_story_events()


def _platinum(tmp_path: Path) -> SimpleNamespace:
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated/vars_flags.txt").write_text(
        "FLAG_ZERO\nFLAG_STEP\nRANGE_START = 1\nVAR_STATE = 16384\nVAR_TARGET\n", encoding="utf-8"
    )
    return SimpleNamespace(platinum=True, root=tmp_path)


def test_platinum_conditions_use_named_flags_and_variables(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    story = _story(
        tmp_path,
        monkeypatch,
        "pokeplatinum,FLAG_STEP,Après l'étape,Avant l'étape,test,,,\n"
        "pokeplatinum,VAR_STATE,,,test,eq,VAR_TARGET,Après la cible\n"
        "pokeplatinum,GetTimeOfDay,,,test,ge,3,La nuit\n"
        "pokeplatinum,CheckWonBattle,,,test,ne,0,\n",
    )
    conditions = ScenarioConditions(_platinum(tmp_path), story)
    path = (
        Condition("flag:1", "=", 0),
        Condition("var:16384", "=", "var:16385"),
        Condition("player_starter", "=", 387),
        Condition("GetTimeOfDay", ">=", 3),
        Condition("CheckWonBattle", "!=", 0),
        Condition("flag:1", "=", 0),
    )
    assert conditions.phrases(path, "test") == ("Avant l'étape", "Après la cible", "La nuit")
    assert story.unused(set(DS_REPOS)) == []


def test_diamond_pearl_keeps_numbers_and_unknown_conditions_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story = _story(tmp_path, monkeypatch, "pokediamond,flag:282,Après le réveil,,test,,,\n")
    conditions = ScenarioConditions(SimpleNamespace(platinum=False, root=tmp_path), story)
    assert conditions.phrases((Condition("flag:282", "=", 1),), "test") == ("Après le réveil",)
    with pytest.raises(ValueError, match="à relire"):
        conditions.phrases((Condition("var:16522", "=", 1),), "test")
    with pytest.raises(ValueError, match="non booléen"):
        conditions.phrases((Condition("flag:282", "!=", 1),), "test")
    with pytest.raises(ValueError, match="non résolue"):
        conditions.phrases((Condition("ScrCmd_Test", "=", "MENU_NO"),), "test")


def test_ds_rows_cannot_mix_older_games(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="même ligne"):
        _story(tmp_path, monkeypatch, "pokeplatinum|pokeemerald,FLAG_X,,,test,,,\n")
    with pytest.raises(ValueError, match="valeur illisible"):
        _story(tmp_path, monkeypatch, "pokediamond,var:1,,,test,eq,MENU_NO,Phrase\n")
