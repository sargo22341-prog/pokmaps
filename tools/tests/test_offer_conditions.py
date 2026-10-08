"""Conditions des offres : modèle, analyse des scripts de la 2e génération et rappels de carte (offer_conditions)."""

from pathlib import Path

import pytest

from pokemaps_data.offer_conditions import (
    ALL_TIMES,
    ALL_WEEKDAYS,
    ALWAYS,
    Condition,
    Requirement,
    solve,
    time_mask,
    weekday_mask,
)
from pokemaps_data.pret_gen2_conditions import Gen2Conditions, object_appearance
from pokemaps_data.pret_gen2_scripts import ScriptFile
from pokemaps_data.pret_models import NpcOffer, merged_offers

MORN, DAY, NITE = 1, 2, 4
MONDAY = weekday_mask("MONDAY")


def test_join_keeps_what_both_paths_have() -> None:
    night = Condition(times=NITE, requirements=frozenset({Requirement("EVENT_A", True), Requirement("EVENT_B", False)}))
    morning = Condition(times=MORN, weekdays=MONDAY, requirements=frozenset({Requirement("EVENT_A", True)}))
    joined = night.join(morning)
    assert joined == Condition(times=NITE | MORN, requirements=frozenset({Requirement("EVENT_A", True)}))


def test_meet_requires_both_and_detects_impossible_conditions() -> None:
    present_at_night = Condition(times=NITE)
    offered_by_day = Condition(times=DAY)
    assert not present_at_night.meet(offered_by_day).possible
    contradictory = ALWAYS.requiring("EVENT_A", True).requiring("EVENT_A", False)
    assert not contradictory.possible
    assert ALWAYS.requiring("EVENT_A", True).without(frozenset({"EVENT_A"})) == ALWAYS


def test_masks_reject_unknown_names() -> None:
    assert time_mask(frozenset()) == ALL_TIMES
    assert time_mask({"MORN", "NITE"}) == MORN | NITE
    with pytest.raises(ValueError, match="Moments de la journée inconnus"):
        time_mask({"EVE"})
    with pytest.raises(ValueError, match="Jour de la semaine inconnu"):
        weekday_mask("FUNDAY")


def test_solve_joins_loops_and_stops_on_endless_scripts() -> None:
    graph = {"a": ["b", "c"], "b": ["d"], "c": ["d"], "d": ["a"]}

    def transfer(point: object, condition: Condition) -> list[tuple[object, Condition]]:
        refined = condition.requiring("EVENT_B", True) if point == "b" else condition
        return [(following, refined) for following in graph[str(point)]]

    states = solve([("a", ALWAYS)], transfer)
    # « d » est atteint par b (qui exige EVENT_B) et par c (qui ne l'exige pas) : rien n'est certain.
    assert states["d"] == ALWAYS

    def endless(point: object, condition: Condition) -> list[tuple[object, Condition]]:
        return [(int(str(point)) + 1, condition)]

    with pytest.raises(ValueError, match="trop longue"):
        solve([(0, ALWAYS)], endless)


def test_merged_offers_keep_what_every_path_requires() -> None:
    gift = NpcOffer("gift_item", item="LURE_BALL", quantity=1)
    after_well = NpcOffer("gift_item", item="LURE_BALL", quantity=1, condition=ALWAYS.requiring("EVENT_WELL", True))
    assert merged_offers([after_well, gift]) == [gift]
    assert merged_offers([after_well]) == [after_well]


_SCRIPT = """\
SiblingScript:
\tfaceplayer
\topentext
\tchecktime NITE
\tiffalse .Day
\tverbosegiveitem TM_CURSE
\tend

.Day
\treadvar VAR_WEEKDAY
\tifnotequal MONDAY, .NotMonday
\tcheckevent EVENT_GOT_SHARP_BEAK
\tiftrue .Done
\tcheckevent EVENT_CLEARED_RADIO_TOWER
\tiffalse .Done
\tverbosegiveitem SHARP_BEAK
\tsetevent EVENT_GOT_SHARP_BEAK
.Done:
\tend

.NotMonday:
\tjumpstd PokecenterNurseScript

Test_MapScripts:
\tdef_callbacks
\tcallback MAPCALLBACK_OBJECTS, TestMerchantCallback
\tcallback MAPCALLBACK_OBJECTS, TestTutorCallback

TestMerchantCallback:
\treadvar VAR_WEEKDAY
\tifequal MONDAY, .Monday
\tdisappear TEST_MERCHANT
\tendcallback

.Monday:
\tdisappear TEST_MERCHANT
\tchecktime MORN
\tiffalse .Done
\tappear TEST_MERCHANT
.Done:
\tendcallback

TestTutorCallback:
\tcheckevent EVENT_BEAT_ELITE_FOUR
\tiffalse .TutorDone
\treadvar VAR_WEEKDAY
\tifequal WEDNESDAY, .Appear
\tdisappear TEST_TUTOR
\tendcallback

.Appear:
\tappear TEST_TUTOR
.TutorDone:
\tendcallback
"""

_STD = """\
PokecenterNurseScript:
\topentext
\tspecial HealParty
\tend
"""


@pytest.fixture()
def scripts(tmp_path: Path) -> tuple[ScriptFile, Gen2Conditions]:
    (tmp_path / "Test.asm").write_text(_SCRIPT, encoding="utf-8")
    (tmp_path / "std_scripts.asm").write_text(_STD, encoding="utf-8")
    std = ScriptFile(tmp_path / "std_scripts.asm")
    return ScriptFile(tmp_path / "Test.asm"), Gen2Conditions(std)


def _at(points: dict, script_file: ScriptFile, line: str) -> Condition:
    """Condition à la ligne `line` du fichier (unique)."""
    found = [
        condition
        for (source, block, index), condition in points.items()
        if source is script_file
        and index < len(source.blocks[block].lines)
        and source.blocks[block].lines[index] == line
    ]
    assert len(found) == 1, line
    return found[0]


def test_gen2_branches_on_time_weekday_and_flags(scripts: tuple[ScriptFile, Gen2Conditions]) -> None:
    script_file, reader = scripts
    points = reader.script_conditions(script_file, "SiblingScript", None)
    assert _at(points, script_file, "verbosegiveitem TM_CURSE") == Condition(times=NITE)
    beak = _at(points, script_file, "verbosegiveitem SHARP_BEAK")
    assert beak.times == MORN | DAY
    assert beak.weekdays == MONDAY
    assert beak.requirements == {
        Requirement("EVENT_GOT_SHARP_BEAK", False),
        Requirement("EVENT_CLEARED_RADIO_TOWER", True),
    }
    # Le script lève lui-même EVENT_GOT_SHARP_BEAK : « déjà donné » n'est pas une étape du scénario.
    own = reader.own_flags(points)
    assert beak.without(own).requirements == {Requirement("EVENT_CLEARED_RADIO_TOWER", True)}
    # Le script commun appelé les autres jours est suivi, avec ce qui y mène.
    heal = [condition for (source, _, _), condition in points.items() if source is not script_file]
    assert heal and all(condition.weekdays == ALL_WEEKDAYS & ~MONDAY for condition in heal)


def test_gen2_callbacks_give_the_days_and_moments_of_presence(scripts: tuple[ScriptFile, Gen2Conditions]) -> None:
    script_file, reader = scripts
    appearance = object_appearance(reader, script_file, frozenset({"TEST_MERCHANT"}))
    # Le marchand n'est là que le lundi matin, comme le Papi du Souterrain de Doublonville.
    assert appearance["TEST_MERCHANT"] == Condition(times=MORN, weekdays=MONDAY)
    # Le tuteur, caché au départ, ne paraît que le mercredi après la Ligue : un chemin qui ne le touche pas le
    # laisse caché.
    tutor = appearance["TEST_TUTOR"]
    assert tutor.weekdays == weekday_mask("WEDNESDAY")
    assert tutor.requirements == {Requirement("EVENT_BEAT_ELITE_FOUR", True)}
    # S'il pouvait déjà être visible, les jours d'avant la Ligue le laisseraient tel quel : rien n'est certain.
    persistent = object_appearance(reader, script_file, frozenset({"TEST_TUTOR"}))
    assert "TEST_TUTOR" not in persistent
