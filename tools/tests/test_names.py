"""Noms affichés des dresseurs, des personnages et des installations (tools/data/)."""

from pathlib import Path

import pytest

from pokemaps_data import maps_characters_data
from pokemaps_data.builder_maps import _complete_character_families
from pokemaps_data.games import EMERALD, GEN3_GAMES
from pokemaps_data.maps import GameMapData
from pokemaps_data.maps_characters_data import CharacterNames, read_character_names


def test_known_names_are_read() -> None:
    names = read_character_names()
    assert names.trainer("youngster") == "Gamin"
    assert names.character("clerk") == "Vendeur"
    assert names.facility("prize_vendor") == "Comptoir des lots"
    assert names.by_text["TEXT_BILLSHOUSE_BILL_SS_TICKET"] == "Léo"


def test_a_missing_name_stops_the_build() -> None:
    names = CharacterNames(trainers={}, characters={})
    with pytest.raises(ValueError, match=r"trainer_classes\.csv"):
        names.trainer("sage")
    with pytest.raises(ValueError, match=r"npc_names\.csv"):
        names.character("kimono-girl")
    with pytest.raises(ValueError, match=r"facility_names\.csv"):
        names.facility("slot_machine")
    with pytest.raises(ValueError, match=r"npc_text_names\.csv"):
        names.text_name("Route25_SeaCottage_EventScript_Bill")


@pytest.mark.parametrize(
    ("filename", "header", "row"),
    [
        ("trainer_classes.csv", "trainer_class,name_fr", "TRAINER_CLASS_TEST,"),
        ("npc_names.csv", "sprite,name_fr,appearance", "OBJ_EVENT_GFX_TEST,,person"),
        ("npc_text_names.csv", "family,text,name_fr", "ruby-sapphire-emerald,ScriptTest,"),
        ("facility_names.csv", "kind,name_fr", "move_tutor,"),
    ],
)
def test_blank_csv_name_stops_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str, header: str, row: str
) -> None:
    (tmp_path / filename).write_text(f"{header}\n{row}\n", encoding="utf-8")
    monkeypatch.setattr(maps_characters_data, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match=filename):
        maps_characters_data._read_csv(filename)


def test_duplicate_csv_key_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "facility_names.csv").write_text("kind,name_fr\nheal,Soins\nheal,Repos\n", encoding="utf-8")
    monkeypatch.setattr(maps_characters_data, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="clé répétée"):
        maps_characters_data._read_csv("facility_names.csv")


def test_gen3_character_and_facility_names() -> None:
    names = read_character_names()
    assert names.trainer("TRAINER_CLASS_AROMA_LADY") == "Aroma"
    assert names.character("OBJ_EVENT_GFX_STEVEN") == "Pierre Rochard"
    assert names.npc_kind("OBJ_EVENT_GFX_ARTICUNO") == "npc_pokemon"
    assert names.facility("battle_point_exchange") == "Comptoir des Points Combat"
    assert names.by_text["Route25_SeaCottage_EventScript_Bill"] == "Léo"
    assert names.by_text["Route114_LanettesHouse_EventScript_Lanette"] == "Annette"


def test_partial_character_preview_does_not_require_names_in_database() -> None:
    data = {game.version_group: GameMapData([], [], [], []) for game in GEN3_GAMES}
    assert _complete_character_families(GEN3_GAMES, data) == {"ruby-sapphire-emerald", "firered-leafgreen"}
    data[EMERALD.version_group] = GameMapData([], [], [], [], characters_complete=False)
    assert _complete_character_families(GEN3_GAMES, data) == {"firered-leafgreen"}
