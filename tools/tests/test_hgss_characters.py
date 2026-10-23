"""Contrats ordinaires de l'audit HGSS, sans cache ni réseau."""

import hashlib
import json
from pathlib import Path

import pytest

from pokemaps_data.pret_hgss_rematches import select_rematch
from pokemaps_data.pret_hgss_scripts import Instruction, Script, reachable, read_script
from pokemaps_data.pret_hgss_trainers import default_attacks
from pokemaps_data.preview_characters_hgss import check_characters
from pokemaps_data.sources import HGSS_PRET_COMMIT
from pokemaps_data.sources_characters_hgss import CONTRACT


def test_character_sources_are_pinned_and_hgss_only() -> None:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["commit"] == HGSS_PRET_COMMIT
    assert len(data["files"]) == 2416
    assert len([name for name in data["files"] if name.endswith(".s") and "scr_seq/" in name]) == 965
    assert "src/overlay_26_022598C0.c" in data["files"]
    assert "files/tel/pmtel_book.json" in data["files"]
    assert all(len(value) == 64 for value in data["files"].values())
    assert not any("vs_seeker" in name for name in data["files"])


def test_default_attacks_ignore_duplicates_and_later_levels() -> None:
    rows = ((1, 1), (1, 2), (3, 3), (4, 4), (5, 2), (6, 5), (10, 6))
    assert default_attacks(rows, 6) == [2, 3, 4, 5]


@pytest.mark.parametrize(
    ("beaten", "unlocked", "expected"),
    [
        (set(), {1, 2, 3, 4}, 10),
        ({10}, {1, 2}, 11),
        ({10, 11}, {1, 2, 3}, 12),
        ({10, 11, 12}, {1, 2, 3, 4}, 13),
        ({10, 11, 12, 13}, {1, 2, 3, 4}, 13),
        ({10, 11}, {1, 2}, 11),
        (set(), set(), 10),
    ],
)
def test_native_rematch_selection(beaten: set[int], unlocked: set[int], expected: int) -> None:
    assert select_rematch([10, 10, 11, 12, 13, 0], beaten, unlocked) == expected


def test_rematch_fallback_does_not_search_for_an_unlocked_group() -> None:
    # Le moteur ne revérifie pas le verrou du niveau de repli.
    assert select_rematch([10, 10, 11, 12, 13, 0], {10, 11}, set()) == 11


def test_rematch_fallback_skips_sentinel() -> None:
    assert select_rematch([10, 10, 65535, 12, 13, 0], {10}, {1}) == 10


def test_script_graph_preserves_branches_and_stops_at_end(tmp_path: Path) -> None:
    path = tmp_path / "script.s"
    path.write_text(
        "\tScrDef entry\n\tScrDefEnd\nentry:\n\tCompare VAR_A, 152\n"
        "\tGoToIfNe other\n\tTrainerBattle TRAINER_A, 0, 0, 0\n\tGoTo done\n"
        "other:\n\tTrainerBattle TRAINER_B, 0, 0, 0\ndone:\n\tEnd\n"
        "unreachable:\n\tTrainerBattle TRAINER_C, 0, 0, 0\n",
        encoding="utf-8",
    )
    script = read_script(path, tmp_path)
    assert script.entries == ("entry",)
    assert reachable(script, "entry") == set(range(6))
    assert script.steps[1].arguments == ("other",)


def test_script_graph_loop_is_bounded() -> None:
    script = Script("loop.s", ("entry",), {"entry": 0}, (Instruction(1, "GoTo", ("entry",)),))
    assert reachable(script, "entry") == {0}


def test_script_rejects_unknown_entry() -> None:
    with pytest.raises(ValueError, match="entrée inconnue"):
        reachable(Script("empty.s", (), {}, ()), "missing")


def test_script_rejects_duplicate_label(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.s"
    path.write_text("\tScrDef entry\nentry:\n\tEnd\nentry:\n\tEnd\n", encoding="utf-8")
    with pytest.raises(ValueError, match="répétée"):
        read_script(path, tmp_path)


def test_script_rejects_missing_jump_destination(tmp_path: Path) -> None:
    path = tmp_path / "missing.s"
    path.write_text("\tScrDef entry\nentry:\n\tGoTo missing\n", encoding="utf-8")
    with pytest.raises(ValueError, match="destination de script inconnue"):
        read_script(path, tmp_path)


def test_character_inventory_rejects_extra_file(tmp_path: Path) -> None:
    (tmp_path / "inventory.json").write_text("{}", encoding="utf-8")
    (tmp_path / "extra.txt").write_text("modifié", encoding="utf-8")
    with pytest.raises(ValueError, match="inventaire des personnages modifié"):
        check_characters(tmp_path)


def test_character_preview_rejects_stale_recipe(tmp_path: Path) -> None:
    path = tmp_path / "characters.json"
    path.write_text(json.dumps(dict(commit=HGSS_PRET_COMMIT, recipe={})), encoding="utf-8")
    (tmp_path / "inventory.json").write_text(
        json.dumps({"characters.json": hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="provenance ou recette des personnages périmée"):
        check_characters(tmp_path)
