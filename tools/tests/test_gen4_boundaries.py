"""Frontières DS testées sans cache ni réseau."""

import json
from pathlib import Path

import pytest

from pokemaps_data.builder_pokemon import _check_represented
from pokemaps_data.games import PLATINUM
from pokemaps_data.pret_evolution_gen4 import _pret_conditions
from pokemaps_data.pret_pokemon_moves_gen4 import read_ds_moves
from pokemaps_data.pret_reader import open_pret
from pokemaps_data.pret_species_gen4 import _platinum, read_json


def test_map_reader_explicitly_refuses_ds(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="lecteur de cartes DS indisponible"):
        open_pret(PLATINUM, tmp_path)


def test_unknown_evolution_condition_is_never_lost() -> None:
    with pytest.raises(ValueError, match="condition_future"):
        _check_represented({"id": "1", "condition_future": "1"})


def test_unknown_engine_evolution_stops_generation() -> None:
    with pytest.raises(ValueError, match="Méthode d'évolution DS inconnue"):
        _pret_conditions(None, "EVO_UNKNOWN", 0)


def test_json_reader_rejects_oversized_or_wrong_root(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="objet JSON attendu"):
        read_json(path)
    with path.open("wb") as handle:
        handle.truncate(4 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match="trop volumineux"):
        read_json(path)


def test_platinum_species_field_order_and_two_argument_evolutions(tmp_path: Path) -> None:
    folder = tmp_path / "eevee"
    folder.mkdir()
    path = folder / "data.json"
    path.write_text(
        json.dumps(
            {
                "base_stats": {
                    "hp": 55,
                    "attack": 55,
                    "defense": 50,
                    "speed": 55,
                    "special_attack": 45,
                    "special_defense": 65,
                },
                "types": ["TYPE_NORMAL", "TYPE_NORMAL"],
                "abilities": ["ABILITY_RUN_AWAY", "ABILITY_ADAPTABILITY"],
                "held_items": {"common": "ITEM_NONE", "rare": "ITEM_NONE"},
                "catch_rate": 45,
                "gender_ratio": "GENDER_RATIO_FEMALE_12_5",
                "hatch_cycles": 35,
                "exp_rate": "EXP_RATE_MEDIUM_FAST",
                "egg_groups": ["EGG_GROUP_FIELD", "EGG_GROUP_FIELD"],
                "evolutions": [["EVO_LEVEL_MOSS_ROCK", "SPECIES_LEAFEON"]],
            }
        ),
        encoding="utf-8",
    )
    row = _platinum(path)
    assert row.stats == (55, 55, 50, 45, 65, 55)
    assert row.types == ("normal",)
    assert row.evolutions == (("EVO_LEVEL_MOSS_ROCK", 0, "LEAFEON"),)


def test_unknown_move_repository_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Dépôt d'attaques DS inconnu"):
        read_ds_moves(tmp_path, "future")
