"""Non-régression du catalogue complet des équipes et de leurs revanches."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.pret_gen3_rematches import RematchTeam, TrainerRematches
from pokemaps_data.pret_gen3_trainers import Gen3Trainer, _party
from pokemaps_data.preview_trainers_gen3 import TrainerCatalog, validate_trainer_catalog, write_trainer_catalogs


def _catalog() -> TrainerCatalog:
    party = _party(
        "{.iv = 255, .lvl = 5, .species = SPECIES_EEVEE, .heldItem = ITEM_ORAN_BERRY, "
        ".moves = {MOVE_TACKLE, MOVE_NONE, MOVE_GROWL, MOVE_NONE}}",
        {"SPECIES_EEVEE": ((1, "MOVE_TACKLE"),)},
        "test",
    )
    trainer = Gen3Trainer("TRAINER_TEST", "TRAINER_CLASS_TWINS", "TEST", True, ("ITEM_POTION",), party)
    teams = (
        RematchTeam(trainer.const, 0, (), ()),
        RematchTeam(trainer.const, 3, ("FLAG_SYS_GAME_CLEAR",), ("Après la Ligue",), (trainer.const,)),
    )
    return TrainerCatalog("test", "test", "pret", "pinned", (trainer,), (TrainerRematches("MAP_TEST", teams),), ())


def test_export_preserves_move_slots_items_doubles_and_repeated_rematches(tmp_path: Path) -> None:
    output = tmp_path / "trainers.json"
    write_trainer_catalogs(output, [_catalog()])
    version = json.loads(output.read_text(encoding="utf-8"))["versions"][0]
    trainer = version["trainers"][0]
    assert trainer["double_battle"] is True
    assert trainer["party"][0]["move_slots"] == ["MOVE_TACKLE", "MOVE_NONE", "MOVE_GROWL", "MOVE_NONE"]
    assert trainer["party"][0]["item"] == "ITEM_ORAN_BERRY"
    assert trainer["party"][0]["iv"] == 255
    teams = version["rematches"][0]["teams"]
    assert [team["stage"] for team in teams] == [0, 3]
    assert teams[1]["previous_trainers"] == ["TRAINER_TEST"]
    assert teams[1]["conditions"] == ["Après la Ligue"]


def test_default_moves_have_four_slots_and_zero_initialized_iv() -> None:
    mon = _party("{.lvl = 5, .species = SPECIES_EEVEE}", {"SPECIES_EEVEE": ((1, "MOVE_TACKLE"),)}, "test")[0]
    assert mon.move_slots == ("MOVE_TACKLE", "MOVE_NONE", "MOVE_NONE", "MOVE_NONE")
    assert mon.iv == mon.fixed_iv == 0
    assert not mon.custom_moves
    assert _catalog().trainers[0].party[0].fixed_iv == 31


@pytest.mark.parametrize("field", [".iv = 256,", ".iv = 20 + 1,", ".heldItem = ITEM_NONE + 1,"])
def test_invalid_numeric_or_item_expression_is_rejected(field: str) -> None:
    with pytest.raises(ValueError, match=r"invalide|illisible"):
        _party("{" + field + ".lvl = 5, .species = SPECIES_EEVEE}", {"SPECIES_EEVEE": ((1, "MOVE_TACKLE"),)}, "test")


def test_missing_rematch_reference_is_rejected() -> None:
    catalog = _catalog()
    team = replace(catalog.rematches[0].teams[1], trainer="TRAINER_ABSENT")
    row = replace(catalog.rematches[0], teams=(catalog.rematches[0].teams[0], team))
    with pytest.raises(ValueError, match="absente"):
        validate_trainer_catalog(replace(catalog, rematches=(row,)))


def test_missing_previous_team_is_rejected() -> None:
    catalog = _catalog()
    team = replace(catalog.rematches[0].teams[1], previous_trainers=())
    row = replace(catalog.rematches[0], teams=(catalog.rematches[0].teams[0], team))
    with pytest.raises(ValueError, match="progression"):
        validate_trainer_catalog(replace(catalog, rematches=(row,)))


def test_duplicate_versions_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="versions"):
        write_trainer_catalogs(tmp_path / "trainers.json", [_catalog(), _catalog()])
