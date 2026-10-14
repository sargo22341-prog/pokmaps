"""Effets des attaques (pret + tools/data/move_effects.csv) et caractéristiques propres à chaque jeu."""

import sqlite3

import pytest

from pokemaps_data.games import PretFormat
from pokemaps_data.pret_moves import GameMoves, PretMove, move_effects

RED_BLUE, YELLOW_GROUP = 1, 2
FIRE_PUNCH, BODY_SLAM, TOXIC, PSYCHIC, DRAGON_RAGE, SLASH = 7, 34, 92, 94, 82, 163
HIDDEN_POWER = 237


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
        move_effects({"red-blue": GameMoves(PretFormat.GEN1, [PretMove("POUND", "UNKNOWN_EFFECT", 40, 35)])})


def test_an_unused_effect_row_stops_the_build() -> None:
    with pytest.raises(ValueError, match="sans attaque correspondante"):
        move_effects({"red-blue": GameMoves(PretFormat.GEN1, [PretMove("POUND", "NO_ADDITIONAL_EFFECT", 40, 35)])})


def test_pp_and_power_come_from_the_game(db: sqlite3.Connection) -> None:
    """PokéAPI garde les valeurs récentes de Repos, E-Coque, Lait à Boire, Lire-Esprit, Paresse et Lumi-Éclat."""
    rows = db.execute(
        """SELECT m.identifier, vg.identifier, v.pp, v.power FROM move_version_group v
           JOIN move m ON m.id = v.move_id JOIN version_group vg ON vg.id = v.version_group_id
           WHERE m.identifier IN ('rest', 'soft-boiled', 'milk-drink', 'mind-reader', 'slack-off', 'luster-purge')"""
    ).fetchall()
    expected_pp = {"rest": 10, "soft-boiled": 10, "milk-drink": 10, "mind-reader": 5, "slack-off": 10}
    assert {row[0] for row in rows} == {*expected_pp, "luster-purge"}
    for move, version_group, pp, power in rows:
        if move == "luster-purge":
            assert power == 70, version_group
        else:
            assert pp == expected_pp[move], (move, version_group)
    # Dégâts fixes ou variables : pas de puissance, malgré la valeur technique écrite dans pret.
    for move_id in (DRAGON_RAGE, HIDDEN_POWER):
        powers = db.execute("SELECT DISTINCT power FROM move_version_group WHERE move_id = ?", (move_id,)).fetchall()
        assert powers == [(None,)], move_id
