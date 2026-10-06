"""Noms affichés des dresseurs et des personnages (tools/data/)."""

import pytest

from pokemaps_data.maps import CharacterNames, read_character_names


def test_known_names_are_read() -> None:
    names = read_character_names()
    assert names.trainer("youngster") == "Gamin"
    assert names.character("clerk") == "Vendeur"


def test_a_missing_name_stops_the_build() -> None:
    names = CharacterNames(trainers={}, characters={})
    with pytest.raises(ValueError, match=r"trainer_classes\.csv"):
        names.trainer("sage")
    with pytest.raises(ValueError, match=r"npc_names\.csv"):
        names.character("kimono-girl")
