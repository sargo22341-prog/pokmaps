"""Extraits C et assembleur des trois moteurs, et rejets à la frontière."""

from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_source import conditional_text, read_initializers, read_json, source_path


@pytest.mark.parametrize(
    ("directive", "symbol", "other"),
    [
        ("#if defined(FIRERED)", "FIRERED", "LEAFGREEN"),
        (".ifdef SAPPHIRE", "SAPPHIRE", "RUBY"),
        ("#ifdef ENGLISH", "ENGLISH", "GERMAN"),
    ],
)
def test_version_branches(tmp_path: Path, directive: str, symbol: str, other: str) -> None:
    prefix = directive[0]
    path = tmp_path / "source.h"
    path.write_text(f"{directive}\nselected\n{prefix}else\nother\n{prefix}endif\n", encoding="utf-8")
    assert conditional_text(path, frozenset({symbol})) == "selected"
    assert conditional_text(path, frozenset({other})) == "other"


@pytest.mark.parametrize(
    "text",
    [
        "#if UNKNOWN\nx\n#endif",
        ".else",
        "#ifdef RUBY\nx",
        "#if RUBY + 1\nx\n#endif",
        "#ifdef RUBY\n#else\n#else\n#endif",
        "#ifdef RUBY\n#else\n#elif SAPPHIRE\n#endif",
        ".elseif RUBY",
    ],
)
def test_unknown_or_unbalanced_conditions_fail(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.inc"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.inc"):
        conditional_text(path, frozenset({"RUBY"}))


def test_nested_numeric_and_boolean_conditions(tmp_path: Path) -> None:
    path = tmp_path / "graphics.c"
    path.write_text(
        "#if DEBUG_FIX || !ENGLISH\nwrong\n#else\n#if REVISION >= 1\nwrong\n"
        "#elif defined(ENGLISH) && !GERMAN\nright\n#endif\n#endif",
        encoding="utf-8",
    )
    assert conditional_text(path, frozenset({"ENGLISH"})) == "right"


def test_conditional_depth_is_bounded(tmp_path: Path) -> None:
    path = tmp_path / "deep.c"
    path.write_text("#ifdef RUBY\n" * 33 + "#endif\n" * 33, encoding="utf-8")
    with pytest.raises(ValueError, match="imbriquées"):
        conditional_text(path, frozenset({"RUBY"}))


@pytest.mark.parametrize("text", ['{"id":1,"id":2}', "[]", '{"broken":}', '{"value":NaN}'])
def test_invalid_json_fails(tmp_path: Path, text: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.json"):
        read_json(path)


def test_source_size_is_bounded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "large.json"
    path.write_text('{"value": 123}', encoding="utf-8")
    monkeypatch.setattr("pokemaps_data.pret_gen3_source.MAX_SOURCE_BYTES", 4)
    with pytest.raises(ValueError, match="volumineuse"):
        read_json(path)


def test_source_paths_cannot_leave_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="hors du dépôt"):
        source_path(tmp_path, "../outside.bin")


@pytest.mark.parametrize(
    "body",
    [
        ".effect = EFFECT_HIT, .effect = EFFECT_BURN_HIT,",
        ".effect = {EFFECT_HIT},",
        ".effect = unknown_call(),",
        "unknown_field,",
        ".effect = EFFECT_HIT}, [MOVE_TEST] = {",
    ],
)
def test_unsupported_initializers_fail(tmp_path: Path, body: str) -> None:
    path = tmp_path / "moves.h"
    path.write_text(f"[MOVE_TEST] = {{{body}}}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"moves\.h"):
        read_initializers(path, "MOVE_")


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_facade_selects_each_version(tmp_path: Path, game: Game) -> None:
    repo = Gen3PretRepo(tmp_path, game.pret_versions)
    for version, symbol in game.pret_versions:
        path = tmp_path / "script.inc"
        path.write_text(f".ifdef {symbol}\nselected\n.else\nother\n.endif", encoding="utf-8")
        assert repo.source_text("script.inc", version) == "selected"
    with pytest.raises(ValueError, match="version inconnue"):
        repo.source_text("script.inc", "unknown")


def test_facade_rejects_missing_versions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="versions GBA invalides"):
        Gen3PretRepo(tmp_path, ())


def test_defined_zero_revision_is_distinct_from_its_value(tmp_path: Path) -> None:
    path = tmp_path / "revision.h"
    path.write_text("#ifdef REVISION\n#if REVISION == 0\nselected\n#endif\n#endif", encoding="utf-8")
    assert conditional_text(path, frozenset({"ENGLISH"})) == "selected"
