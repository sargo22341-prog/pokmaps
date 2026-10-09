"""Équipes GBA : moteur des attaques, variantes C et revanches épinglées."""

from pathlib import Path

import pytest

from pokemaps_data.games import GEN3_GAMES, Game
from pokemaps_data.maps_layout import read_layout_curation
from pokemaps_data.maps_layout_gen3 import Gen3GameMaps
from pokemaps_data.pret_gen3 import Gen3PretRepo
from pokemaps_data.pret_gen3_rematches import _validate_remake_conditions
from pokemaps_data.pret_gen3_trainers import _blocks, _party, default_moves
from pokemaps_data.preview_trainers_gen3 import trainer_catalogs, write_trainer_catalogs
from pokemaps_data.sources import pret_dir


def test_default_moves_preserve_order_and_ignore_known_duplicates() -> None:
    learnset = ((1, "A"), (1, "B"), (4, "C"), (7, "D"), (10, "A"), (12, "E"), (15, "F"))
    assert default_moves(learnset, 1) == ("A", "B")
    assert default_moves(learnset, 10) == ("A", "B", "C", "D")
    assert default_moves(learnset, 12) == ("B", "C", "D", "E")
    assert default_moves(learnset, 15) == ("C", "D", "E", "F")


def test_default_moves_can_relearn_a_move_that_was_forgotten() -> None:
    learnset = tuple((1, name) for name in ("A", "B", "C", "D", "E", "A"))
    assert default_moves(learnset, 1) == ("C", "D", "E", "A")


@pytest.mark.parametrize("level", [0, 101])
def test_invalid_level_is_rejected(level: int) -> None:
    with pytest.raises(ValueError, match="Niveau"):
        default_moves(((1, "A"),), level)


def test_missing_initial_move_is_rejected() -> None:
    with pytest.raises(ValueError, match="Aucune attaque"):
        default_moves(((5, "A"),), 1)


@pytest.mark.parametrize("field", ["level", "lvl"])
@pytest.mark.parametrize("braces", [False, True])
def test_explicit_party_keeps_moves_and_held_item(field: str, braces: bool) -> None:
    moves = "MOVE_TACKLE, MOVE_GROWL, MOVE_NONE, MOVE_NONE"
    if braces:
        moves = "{" + moves + "}"
    body = (
        "{" + f".iv = 20, .{field} = 5, .species = SPECIES_EEVEE, .heldItem = ITEM_ORAN_BERRY, .moves = {moves}" + "}"
    )
    party = _party(body, {"SPECIES_EEVEE": ((1, "MOVE_TACKLE"),)}, "test")
    assert len(party) == 1
    assert party[0].level == 5
    assert party[0].item == "ITEM_ORAN_BERRY"
    assert party[0].moves == ("MOVE_TACKLE", "MOVE_GROWL")


def test_unknown_species_is_rejected() -> None:
    with pytest.raises(ValueError, match="Pokémon illisible"):
        _party("{.lvl = 5, .species = SPECIES_EEVEE}", {}, "test")


def test_truncated_custom_moves_are_rejected() -> None:
    with pytest.raises(ValueError, match="quatre attaques"):
        _party("{.lvl = 5, .species = SPECIES_EEVEE, .moves = {MOVE_TACKLE}}", {"SPECIES_EEVEE": ()}, "test")


@pytest.mark.parametrize("body", ["[A] = {", "[A] = {} [A] = {}"])
def test_invalid_initializer_is_rejected(body: str) -> None:
    with pytest.raises(ValueError, match="Initialiseur"):
        _blocks(body, r"\[(\w+)\]\s*=\s*\{")


def test_rematch_gate_change_is_rejected() -> None:
    with pytest.raises(ValueError, match="conditions du moteur"):
        _validate_remake_conditions(
            "static void TryGetRematchTrainerIdGivenGameState(void) {\ncase 1: if (!FlagGet(FLAG_WRONG))\n}"
        )


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_pinned_trainers_and_rematches(source_cache_ready: None, game: Game) -> None:
    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    expected = {"ruby-sapphire": (693, 56), "emerald": (854, 78), "firered-leafgreen": (742, 221)}
    trainer_count, rematch_count = expected[game.version_group]
    for version, _ in game.pret_versions:
        assert len(repo.trainers[version]) == trainer_count
        assert len(repo.rematches[version]) == rematch_count
        for trainer in repo.trainers[version].values():
            assert 1 <= len(trainer.party) <= 6
            assert all(1 <= len(mon.moves) <= 4 for mon in trainer.party)
        for rematch in repo.rematches[version]:
            assert all(team.trainer in repo.trainers[version] for team in rematch.teams)


@pytest.mark.parametrize("game", GEN3_GAMES, ids=lambda game: game.version_group)
def test_pinned_catalog_export(source_cache_ready: None, game: Game, tmp_path: Path) -> None:
    import json

    from pokemaps_data.sources import PRET_COMMITS

    repo = Gen3PretRepo(pret_dir(Path(__file__).resolve().parents[1] / ".cache", game.pret_repo), game.pret_versions)
    catalogs = list(trainer_catalogs(Gen3GameMaps(repo, game, read_layout_curation())))
    output = tmp_path / "trainers.json"
    write_trainer_catalogs(output, catalogs)
    versions = json.loads(output.read_text(encoding="utf-8"))["versions"]
    for catalog, exported in zip(catalogs, versions, strict=True):
        assert len(exported["trainers"]) == len(catalog.trainers)
        assert sum(len(row["teams"]) for row in exported["rematches"]) == sum(
            len(row.teams) for row in catalog.rematches
        )
        assert exported["commit"] == PRET_COMMITS[game.pret_repo]
        assert len(exported["bindings"]) == len(catalog.bindings) > 0
        assert all(binding["map_const"] in repo.maps for binding in exported["bindings"])
        assert all(len(mon["move_slots"]) == 4 for trainer in exported["trainers"] for mon in trainer["party"])


def test_pinned_double_battle_and_rematch_gates(source_cache_ready: None) -> None:
    root = Path(__file__).resolve().parents[1] / ".cache"
    emerald_game = next(game for game in GEN3_GAMES if game.version_group == "emerald")
    repo = Gen3PretRepo(pret_dir(root, emerald_game.pret_repo), emerald_game.pret_versions)
    assert repo.trainers["emerald"]["TRAINER_TATE_AND_LIZA_1"].double_battle
    roxanne = next(row for row in repo.rematches["emerald"] if row.teams[0].trainer == "TRAINER_ROXANNE_1")
    assert roxanne.teams[1].flags == ("FLAG_SYS_GAME_CLEAR",)
    assert "FLAG_WATTSON_REMATCH_AVAILABLE" in roxanne.teams[2].flags
    regular = next(row for row in repo.rematches["emerald"] if row.teams[0].trainer == "TRAINER_ROSE_1")
    assert any("ou appel" in condition for condition in regular.teams[1].conditions)
    remake_game = next(game for game in GEN3_GAMES if game.version_group == "firered-leafgreen")
    remake = Gen3PretRepo(pret_dir(root, remake_game.pret_repo), remake_game.pret_versions)
    ben = next(row for row in remake.rematches["firered"] if row.teams[0].trainer == "TRAINER_YOUNGSTER_BEN")
    assert [team.stage for team in ben.teams] == [0, 1, 3, 4]
    assert ben.teams[-1].flags == ("FLAG_SYS_GAME_CLEAR",)
    assert ben.teams[2].previous_trainers == ("TRAINER_YOUNGSTER_BEN", "TRAINER_YOUNGSTER_BEN_2")
