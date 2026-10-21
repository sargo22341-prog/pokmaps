"""Frontières binaires et isolement de l'aperçu Pokémon HGSS, sans cache ni réseau."""

import json
import struct
from dataclasses import replace
from pathlib import Path

import pytest

from pokemaps_data.evolution_hgss import evolution_rows
from pokemaps_data.pret_hgss_pokemon import HgssPokemon, read_level_moves, read_move, validate_personal
from pokemaps_data.preview_pokemon_hgss import _replace_preview, build_hgss_pokemon, validate_comparison
from pokemaps_data.sources import DATA_DIR


def _empty_data() -> HgssPokemon:
    return HgssPokemon((), (), (), (), (), (), ())


def test_level_moves_decode_nine_bit_move_and_seven_bit_level() -> None:
    assert read_level_moves(struct.pack("<4H", (100 << 9) | 467, (1 << 9) | 33, 65535, 0), "fixture") == (
        (100, 467),
        (1, 33),
    )
    assert read_level_moves(b"\xff\xff\x00\x00", "empty") == ()


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\xff",
        b"\x21\x02",
        b"\xff\xff\x01\x00",
        struct.pack("<2H", 33, 65535),
        struct.pack("<2H", 512 | 468, 65535),
    ],
)
def test_level_moves_reject_invalid_or_unterminated_data(data: bytes) -> None:
    with pytest.raises(ValueError, match="fixture"):
        read_level_moves(data, "fixture")


def test_move_keeps_signed_priority_and_physical_special_class() -> None:
    data = struct.pack("<H6BHb3B2x", 12, 1, 90, 10, 100, 15, 0, 0, -6, 1, 2, 3)
    move = read_move(data, 53)
    assert (move["damage_class"], move["priority"], move["power"], move["type"]) == ("special", -6, 90, 10)


@pytest.mark.parametrize(
    "data", [bytes(15), bytes(16), struct.pack("<H6BHb3B2x", 0, 3, 40, 0, 100, 10, 0, 0, 0, 0, 0, 0)]
)
def test_move_rejects_invalid_profile(data: bytes) -> None:
    with pytest.raises(ValueError, match="waza_tbl membre 1"):
        read_move(data, 1)


def test_personal_rejects_invalid_machine_and_stat() -> None:
    row = dict.fromkeys(("hp", "atk", "def", "speed", "spatk", "spdef"), 45)
    row |= dict(
        catchRate=45, friendship=70, tms=[93], hms=[], types=[1, 1], abilities=[1, 0], items=[0, 0], eggGroups=[1, 1]
    )
    with pytest.raises(ValueError, match="tms"):
        validate_personal(row, "fixture")
    with pytest.raises(ValueError, match="statistiques"):
        validate_personal(row | {"hp": 0}, "fixture")


def test_evolution_distinguishes_other_game_trade_and_local() -> None:
    rules = json.loads((DATA_DIR / "hgss_pokemon_rules.json").read_text("utf-8"))
    evos = (
        {
            "baseSpecies": "SPECIES_EEVEE",
            "evos": [
                dict(method="EVO_ETERNA", param=0, target="SPECIES_LEAFEON"),
                dict(method="EVO_FRIENDSHIP_DAY", param=0, target="SPECIES_ESPEON"),
            ],
        },
        {"baseSpecies": "SPECIES_HAUNTER", "evos": [dict(method="EVO_TRADE", param=0, target="SPECIES_GENGAR")]},
    )
    rows = evolution_rows(replace(_empty_data(), evolutions=evos), rules, {})
    assert [r["access"] for r in rows] == ["other-game", "local", "trade"]
    assert "220" in rows[1]["condition_fr"]


def test_unknown_evolution_is_an_error() -> None:
    data = replace(
        _empty_data(),
        evolutions=({"baseSpecies": "fixture", "evos": [dict(method="EVO_MODERN", param=1, target="fixture")]},),
    )
    with pytest.raises(ValueError, match="méthode d'évolution inconnue"):
        evolution_rows(data, {"evolution_access": []}, {})


def test_unexplained_source_difference_is_rejected() -> None:
    comparison = dict(learnset_differences=[], stat_differences=[], profile_differences=[{"species": 1}])
    with pytest.raises(ValueError, match="inexpliquée"):
        validate_comparison(comparison, {"comparison_capture_rates": []})


def test_preview_cannot_overwrite_assets_or_cache(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="séparé"):
        build_hgss_pokemon(tmp_path, tmp_path, tmp_path / "hgss-pokemon")


def test_failed_replacement_preserves_previous_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target, staging, previous = (tmp_path / name for name in ("target", "staging", "previous"))
    target.mkdir()
    staging.mkdir()
    (target / "valid.json").write_text("valid", encoding="utf-8")
    rename = Path.rename

    def fail_staging(path: Path, destination: Path) -> Path:
        if path == staging:
            raise OSError("fixture : remplacement impossible")
        return rename(path, destination)

    monkeypatch.setattr(Path, "rename", fail_staging)
    with pytest.raises(OSError, match="fixture"):
        _replace_preview(staging, target, previous)
    assert (target / "valid.json").read_text("utf-8") == "valid"
