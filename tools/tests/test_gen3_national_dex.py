"""Déblocage du National : preuves dans les scripts et le protocole d'échange épinglés."""

import re
from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_source import read_text
from pokemaps_data.sources import pret_dir


def _repo(game: Game) -> Gen3PretRepo:
    return Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_national_dex_decision_matches_pinned_unlock_sources(source_cache_ready: None, game: Game) -> None:
    assert game.national_dex
    repo = _repo(game)
    if repo.ruby:
        text = read_text(repo.root / "src/trade.c")
        match = re.search(r"static void sub_804BA64\(void\)\s*\{([^{}]+)\}", text)
        assert match is not None
        body = " ".join(match[1].split())
        assert "if (gLinkPlayers[mpId ^ 1].lp_field_2 == 0x8000) EnableNationalPokedex();" in body
        assert "SPECIES" not in body and "GetMonData" not in body
        assert "if (gReceivedRemoteLinkPlayers)\n        sub_804BA64();" in text
    elif repo.remake:
        for version, _ in game.pret_versions:
            _check_oak(repo.source_text("data/maps/PalletTown_ProfessorOaksLab/scripts.inc", version))
    else:
        _check_birch(repo)


def _check_oak(text: str) -> None:
    assert "goto_if_set FLAG_SYS_GAME_CLEAR, PalletTown_ProfessorOaksLab_EventScript_TryStartNationalDexScene" in text
    match = re.search(r"PalletTown_ProfessorOaksLab_EventScript_TryStartNationalDexScene::(.*?)(?=\n\w+::)", text, re.S)
    assert match is not None
    assert "goto_if_lt VAR_0x8009, 60," in match[1]
    assert "goto_if_unset FLAG_WORLD_MAP_ONE_ISLAND," in match[1]
    assert "goto PalletTown_ProfessorOaksLab_EventScript_NationalDexScene" in match[1]
    assert "special EnableNationalPokedex" in text


def _check_birch(repo: Gen3PretRepo) -> None:
    hall = read_text(repo.root / "data/scripts/hall_of_fame.inc")
    assert "call_if_eq VAR_DEX_UPGRADE_JOHTO_STARTER_STATE, 0," in hall
    assert "setvar VAR_DEX_UPGRADE_JOHTO_STARTER_STATE, 1" in hall
    lab = read_text(repo.root / "data/maps/LittlerootTown_ProfessorBirchsLab/scripts.inc")
    assert (
        "map_script_2 VAR_DEX_UPGRADE_JOHTO_STARTER_STATE, 1, "
        "LittlerootTown_ProfessorBirchsLab_EventScript_UpgradeToNationalDex"
    ) in lab
    match = re.search(
        r"LittlerootTown_ProfessorBirchsLab_EventScript_UpgradeToNationalDex::(.*?)(?=\n\w+::)", lab, re.S
    )
    assert match is not None
    assert "special EnableNationalPokedex" in match[1]
    assert "setvar VAR_DEX_UPGRADE_JOHTO_STARTER_STATE, 2" in match[1]
    assert "GetPokedexCount" not in match[1]


@pytest.mark.parametrize("game", GEN3_GAMES[1:], ids=lambda game: game.version_group)
def test_later_games_send_the_ruby_sapphire_national_unlock_marker(source_cache_ready: None, game: Game) -> None:
    text = read_text(_repo(game).root / "src/link.c")
    assert "gLocalLinkPlayer.lp_field_2 = 0x8000;" in text
