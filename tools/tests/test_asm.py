import pytest

from pokemaps_data.asm import directive, labelled_blocks, parse_number, preprocess, strip_comment


def test_strip_comment_keeps_semicolons_in_strings():
    assert strip_comment('db "A;B" ; commentaire') == 'db "A;B" '


def test_preprocess_selects_version_branch():
    text = """
Label:
IF DEF(_RED)
    db 1, RED_ONLY
ENDC
IF DEF(_BLUE)
    db 2, BLUE_ONLY
ELSE
    db 3, NOT_BLUE
ENDC
    db 4, COMMON ; commentaire
"""
    assert preprocess(text, {"_RED"}) == ["Label:", "db 1, RED_ONLY", "db 3, NOT_BLUE", "db 4, COMMON"]
    assert preprocess(text, {"_BLUE"}) == ["Label:", "db 2, BLUE_ONLY", "db 4, COMMON"]


def test_preprocess_skips_macros():
    text = """
MACRO wild
IF _NARG == 4
    db \\1
ENDC
ENDM
    db 5
"""
    assert preprocess(text, set()) == ["db 5"]


def test_preprocess_rejects_unknown_condition():
    with pytest.raises(ValueError):
        preprocess("IF FOO == 1\nENDC", set())


@pytest.mark.parametrize(("token", "value"), [("12", 12), ("$1F", 31), ("%101", 5)])
def test_parse_number(token, value):
    assert parse_number(token) == value


def test_directive():
    assert directive("db 3, PIDGEY") == ("db", ["3", "PIDGEY"])


def test_labelled_blocks_handles_local_labels():
    blocks = labelled_blocks(["Data:", "db 1", ".Group1:", "db 2"])
    assert blocks == {"Data": ["db 1"], "Data.Group1": ["db 2"]}
