"""Contrat des sources de personnages HGSS, distinct des lecteurs Sinnoh."""

import hashlib
import json
from pathlib import Path

from .sources import HGSS_PRET_COMMIT, POKEAPI_COMMIT

CONTRACT = Path(__file__).resolve().parents[2] / "docs/generations/personnages-hgss-sources.json"


def source_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix in {".c", ".h", ".s", ".csv", ".json", ".py"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def character_source_paths(root: Path) -> list[Path]:
    files = [
        "src/data/map_headers.h",
        "include/constants/maps.h",
        "include/constants/trainers.h",
        "include/constants/species.h",
        "include/constants/moves.h",
        "include/constants/items.h",
        "include/constants/std_script.h",
        "include/constants/mmodel.h",
        "include/constants/flags.h",
        "files/poketool/trainer/trainers.json",
        "files/poketool/personal/wotbl.narc",
        "files/tel/pmtel_book.json",
        "src/overlay_26_022598C0.c",
        "src/sys_flags.c",
        "src/script_manager.c",
        "src/scrcmd_battle.c",
        "src/scrcmd_mart.c",
        "src/field/scrcmd_move_tutor.c",
        "src/data/fieldmap/hidden_items.h",
        "files/itemtool/itemdata/item_data.csv",
        "asm/overlay_01_sprite_data.s",
        "asm/unk_02031B0C.s",
        "src/apricorn_tree_sys.c",
        "src/unk_02055418.c",
        "src/field/scrcmd_pokemon_misc.c",
        "src/scrcmd_apricorn.c",
        "asm/macros/script.inc",
        "files/a/1/1/2",
        "src/application/pokegear/phone/scripts/phone_scripts_gym_leader.c",
        "src/application/pokegear/phone/scripts/phone_scripts_generic.c",
        "src/unk_020932A4.c",
        "include/config.h",
        "src/data/fieldmap/script_cmd_table.h",
        "src/application/pokegear/phone/phone_generic_headers.c",
        "src/application/pokegear/phone/phone_script_defs.c",
        "src/gf_rtc.c",
        "src/mom_gift.c",
        "src/save_pokegear.c",
        "src/get_egg.c",
        "asm/overlay_87.s",
        "src/overlay_03/shop_menu.c",
        "src/seal_case.c",
    ]
    paths = [root / name for name in files]
    for folder, pattern in (
        ("files/fielddata/script/scr_seq", "*.s"),
        ("files/fielddata/eventdata/zone_event", "*.json"),
        ("files/data/mmodel/mmodel", "*.NSBTX"),
    ):
        paths.extend(sorted((root / folder).glob(pattern)))
    paths.extend(sorted((root / "include/constants").glob("*.h")))
    paths.extend(sorted((root / "src").rglob("scrcmd*.c")))
    paths = sorted(set(paths))
    if not 1400 <= len(paths) <= 4000:
        raise ValueError("HGSS : inventaire des personnages hors limite")
    return paths


def validate_character_sources(root: Path) -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("HGSS : contrat des personnages d'un autre commit")
    actual = {p.relative_to(root).as_posix(): source_digest(p) for p in character_source_paths(root)}
    if actual != contract["files"]:
        changed = sorted(
            name for name in actual.keys() | contract["files"].keys() if actual.get(name) != contract["files"].get(name)
        )
        raise ValueError(f"HGSS : sources de personnages modifiées : {changed[:10]}")
    if contract["french"] != french_sources(root):
        raise ValueError("HGSS : sources françaises de personnages modifiées")
    return contract


def french_sources(root: Path) -> dict:
    folder = root.parent / f"pokeapi-{POKEAPI_COMMIT[:12]}"
    names = (
        "pokemon_species",
        "pokemon_species_names",
        "moves",
        "move_names",
        "items",
        "item_names",
        "abilities",
        "ability_names",
        "types",
        "type_names",
    )
    return dict(commit=POKEAPI_COMMIT, files={f"{name}.csv": source_digest(folder / f"{name}.csv") for name in names})
