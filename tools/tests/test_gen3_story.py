"""Présence des personnages GBA et traduction explicite des variables de scénario."""

from pathlib import Path

import pytest

from pokemaps_data import story_events
from pokemaps_data.pret_gen3_conditions import ScriptRequirement
from pokemaps_data.pret_gen3_maps import Gen3Event
from pokemaps_data.pret_gen3_offers import Gen3Offers, script_offers
from pokemaps_data.pret_gen3_scripts import Gen3Scripts, parse_scripts
from pokemaps_data.story_events import read_story_events


def test_presence_is_applied_before_exploring_the_script() -> None:
    scripts = Gen3Scripts(
        parse_scripts(
            "Entry:\ngoto_if_set FLAG_HIDE_TEST, Hidden\ngiveitem ITEM_POTION\nend\n"
            "Hidden:\ngiveitem ITEM_ANTIDOTE\nend",
            "test.inc",
        ),
        {"FLAG_HIDE_TEST": 1},
    )
    reader = Gen3Offers.__new__(Gen3Offers)
    reader.scripts = scripts
    event = Gen3Event("object", 1, 2, 0, (("script", "Entry"), ("flag", "FLAG_HIDE_TEST")))
    result = reader.read_object(event)
    assert [offer.item for offer in result.offers] == ["ITEM_POTION"]
    assert result.offers[0].paths == (frozenset({ScriptRequirement("FLAG_HIDE_TEST", "eq", "FALSE")}),)


def test_contradictory_initial_requirements_are_rejected() -> None:
    scripts = Gen3Scripts(parse_scripts("Entry:\ngiveitem ITEM_POTION\nend", "test.inc"), {})
    requirements = frozenset({ScriptRequirement("VAR_STORY", "gt", "4"), ScriptRequirement("VAR_STORY", "lt", "3")})
    assert not script_offers(scripts, "Entry", requirements).offers


def test_symbolic_story_intervals_cannot_produce_impossible_offers() -> None:
    scripts = Gen3Scripts(
        parse_scripts(
            "Entry:\ngoto_if_lt VAR_STORY, STORY_LATE, Done\n"
            "goto_if_ge VAR_STORY, STORY_EARLY, Done\ngiveitem ITEM_POTION\nDone:\nend",
            "test.inc",
        ),
        {"STORY_LATE": 4, "STORY_EARLY": 2},
    )
    assert not script_offers(scripts, "Entry").offers


def test_story_variable_is_translated_and_tracked() -> None:
    events = read_story_events()
    requirement = ScriptRequirement("VAR_DEX_UPGRADE_JOHTO_STARTER_STATE", "eq", "6")
    assert events.script_phrases("pokeemerald", frozenset({requirement}), "test") == (
        "Après avoir choisi le starter de Johto",
    )
    assert "pokeemerald:VAR_DEX_UPGRADE_JOHTO_STARTER_STATE:eq:6" not in events.unused({"pokeemerald"})
    with pytest.raises(ValueError, match="à relire"):
        events.script_phrases("pokeemerald", frozenset({ScriptRequirement("VAR_UNKNOWN", "eq", "1")}), "test")


def test_hexadecimal_script_values_use_the_reviewed_decimal_comparison() -> None:
    events = read_story_events()
    assert events.script_phrases(
        "pokeemerald", frozenset({ScriptRequirement("VAR_DEX_UPGRADE_JOHTO_STARTER_STATE", "eq", "0x6")}), "test"
    ) == ("Après avoir choisi le starter de Johto",)


def test_duplicate_comparison_aliases_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "story_events.csv").write_text(
        "repos,flag,when_set,when_clear,reason,operator,value,phrase\n"
        "pokeemerald,VAR_STORY,,,source,eq,6,Après la scène\n"
        "pokeemerald,VAR_STORY,,,source,eq,0x6,Après la scène\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(story_events, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="deux fois"):
        read_story_events()


@pytest.mark.parametrize("operator,value", [("bad", "1"), ("eq", ""), ("eq", "65536"), ("eq", "text")])
def test_invalid_variable_rows_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operator: str, value: str) -> None:
    (tmp_path / "story_events.csv").write_text(
        "repos,flag,when_set,when_clear,reason,operator,value,phrase\n"
        f"pokeemerald,VAR_STORY,,,source,{operator},{value},Après la scène\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(story_events, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match=r"story_events\.csv"):
        read_story_events()
