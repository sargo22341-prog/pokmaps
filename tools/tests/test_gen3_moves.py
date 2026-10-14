"""Attaques GBA : extraits des trois tables et pourcentages du moteur."""

from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import GEN3_GAMES, Game, PretFormat
from pokemaps_data.pret_gen3_moves import read_moves
from pokemaps_data.pret_moves import GameMoves, PretMove, move_effects
from pokemaps_data.sources import pret_dir


@pytest.mark.parametrize("extension", ["h", "c"])
def test_gba_secondary_chance_is_a_percent(tmp_path: Path, extension: str) -> None:
    path = tmp_path / f"src/data/battle_moves.{extension}"
    path.parent.mkdir(parents=True)
    path.write_text(
        "const struct BattleMove gBattleMoves[] = {\n"
        "[MOVE_NONE] = {.effect = EFFECT_HIT, .power = 0, .pp = 0, .secondaryEffectChance = 0,},\n"
        "[MOVE_EMBER] = {.effect = EFFECT_BURN_HIT, .power = 40, .pp = 25, .secondaryEffectChance = 10,},\n"
        "[MOVE_POUND] = {.effect = EFFECT_HIT, .power = 40, .pp = 35, .secondaryEffectChance = 0,},\n};",
        encoding="utf-8",
    )
    moves = read_moves(tmp_path)
    assert [move.const for move in moves] == ["EMBER", "POUND"]
    assert moves[0].chance_percent == 10
    assert (moves[0].power, moves[0].pp) == (40, 25)
    assert moves[0].chance_256 is None
    assert moves[1].chance_percent is None


@pytest.mark.parametrize(
    "fields",
    [
        ".effect = EFFECT_HIT,",
        ".effect = OTHER, .secondaryEffectChance = 10,",
        ".effect = EFFECT_HIT, .secondaryEffectChance = 101,",
    ],
)
def test_invalid_move_data_fails(tmp_path: Path, fields: str) -> None:
    path = tmp_path / "src/data/battle_moves.h"
    path.parent.mkdir(parents=True)
    path.write_text(f"[MOVE_POUND] = {{{fields}}}", encoding="utf-8")
    with pytest.raises(ValueError, match=r"battle_moves\.h"):
        read_moves(tmp_path)


@pytest.mark.pipeline
@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_all_pinned_moves_have_french_effects(game: Game, source_cache_ready: None) -> None:
    root = pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo)
    moves = read_moves(root)
    assert len(moves) == 354
    assert len({move.const for move in moves}) == 354
    effects = move_effects({game.version_group: GameMoves(PretFormat.GEN3, moves)})[game.version_group]
    assert effects["EMBER"].chance == 10
    assert effects["THUNDER"].chance == 30
    assert effects["POUND"].chance is None
    assert "poids" in effects["LOW_KICK"].description_fr
    assert "Stockages" in effects["SWALLOW"].description_fr


def test_builder_caches_its_gen3_reader(gen3_builder: DatabaseBuilder) -> None:
    for game in GEN3_GAMES:
        reader = gen3_builder.gen3_repo(game, "les cartes")
        assert gen3_builder.gen3_repo(game, "les attaques") is reader
        assert len(reader.moves) == 354
        assert len(gen3_builder.moves.effects[gen3_builder.vg_ids[GEN3_GAMES.index(game)]]) == 354


def test_probabilities_cannot_mix_units() -> None:
    with pytest.raises(ValueError, match="deux unités"):
        PretMove("EMBER", "EFFECT_BURN_HIT", 40, 25, chance_256=25, chance_percent=10)
