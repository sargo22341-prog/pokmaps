"""Effets des attaques (pret + tools/data/move_effects.csv) et caractéristiques propres à chaque jeu."""

import sqlite3

import pytest

from pokemaps_data.games import PretFormat
from pokemaps_data.pret_moves import GameMoves, PretMove, move_effects

RED_BLUE, YELLOW_GROUP = 1, 2
FIRE_PUNCH, BODY_SLAM, TOXIC, PSYCHIC, DRAGON_RAGE, SLASH = 7, 34, 92, 94, 82, 163


def _effect(db: sqlite3.Connection, move_id: int, version_group: int = RED_BLUE) -> tuple[str, float | None]:
    return db.execute(
        "SELECT effect_fr, effect_chance FROM move_version_group WHERE move_id = ? AND version_group_id = ?",
        (move_id, version_group),
    ).fetchone()


def test_every_move_has_an_effect(db: sqlite3.Connection) -> None:
    empty = db.execute("SELECT move_id FROM move_version_group WHERE trim(effect_fr) = ''").fetchall()
    assert empty == []


def test_side_effect_chances_come_from_the_battle_engine(db: sqlite3.Connection) -> None:
    # Chances sur 256 du moteur de la 1re génération : 10 percent + 1, 30 percent + 1, 33 percent + 1.
    assert _effect(db, FIRE_PUNCH)[1] == pytest.approx(26 / 256 * 100)
    assert _effect(db, BODY_SLAM)[1] == pytest.approx(77 / 256 * 100)
    assert _effect(db, PSYCHIC)[1] == pytest.approx(85 / 256 * 100)
    assert "Spécial" in _effect(db, PSYCHIC)[0]


@pytest.mark.parametrize("version_group", [RED_BLUE, YELLOW_GROUP])
def test_move_specific_texts(db: sqlite3.Connection, version_group: int) -> None:
    assert _effect(db, TOXIC, version_group) == (
        "Empoisonne gravement la cible : les dégâts du poison augmentent à chaque tour "
        "(sauf un Pokémon de type Poison).",
        None,
    )
    assert _effect(db, DRAGON_RAGE, version_group) == ("Inflige toujours 40 PV de dégâts.", None)
    assert "coups critiques" in _effect(db, SLASH, version_group)[0]


def test_an_effect_without_text_stops_the_build() -> None:
    with pytest.raises(ValueError, match="UNKNOWN_EFFECT"):
        move_effects({"red-blue": GameMoves(PretFormat.GEN1, [PretMove("POUND", "UNKNOWN_EFFECT")])})


def test_an_unused_effect_row_stops_the_build() -> None:
    with pytest.raises(ValueError, match="sans attaque correspondante"):
        move_effects({"red-blue": GameMoves(PretFormat.GEN1, [PretMove("POUND", "NO_ADDITIONAL_EFFECT")])})
