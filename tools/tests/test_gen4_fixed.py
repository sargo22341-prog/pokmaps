"""Pokémon fixes DS sur des sources réduites : personnages posés par le moteur du Monde Distorsion et constantes
`#define` des en-têtes qu'incluent les macros de Platine."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pokemaps_data.pret_gen4_distortion import read_distortion_objects
from pokemaps_data.pret_gen4_flow_chains import Condition
from pokemaps_data.pret_gen4_source import included_defines

_OBJECT = """static const DistWorldObjectEvent {name} = {{
    .flagCond = {condition},
    .flagCondVal = {value},
    .rotated = FALSE,
    .objEvent = {{
        .localID = 0,
        .hiddenFlag = {flag},
        .script = {script},
        .x = 0xF,
        .z = 0xD,
        .y = (1 << 4) * FX32_ONE,
    }},
}};
"""


def _distortion(root: Path, objects: str, table: str) -> SimpleNamespace:
    (root / "src/overlay009").mkdir(parents=True)
    (root / "generated").mkdir()
    (root / "include/constants").mkdir(parents=True)
    (root / "src/system_vars.c").write_text(
        "u16 SystemVars_GetDistortionWorldProgress(VarsFlags *varsFlags)\n"
        "{\n    return TryGetVarValue(varsFlags, VAR_DISTORTION_WORLD_PROGRESS);\n}\n",
        encoding="utf-8",
    )
    (root / "generated/vars_flags.txt").write_text(
        "FLAG_OBTAINED_ORB = 1000\nVAR_A = 16468\nVAR_DISTORTION_WORLD_PROGRESS\n", encoding="utf-8"
    )
    (root / "include/script_manager.h").write_text("#define SCRIPT_ID_OFFSET_VISIBLE_ITEMS 7000\n", encoding="utf-8")
    (root / "include/constants/distortion_world.h").write_text(
        "enum DistWorldProgress {\n    DIST_WORLD_PROGRESS_NONE = 0,\n    DIST_WORLD_PROGRESS_ARRIVED = 13,\n};\n",
        encoding="utf-8",
    )
    (root / "src/overlay009/ov9_02249960.c").write_text(objects + table, encoding="utf-8")
    return SimpleNamespace(root=root, platinum=True)


def test_distortion_objects_keep_their_progress_condition(tmp_path: Path) -> None:
    giratina = _OBJECT.format(
        name="sGiratina",
        condition="FLAG_COND_WORLD_PROGRESS_EQ",
        value="DIST_WORLD_PROGRESS_ARRIVED",
        flag="0x0",
        script="0x5",
    )
    orb = _OBJECT.format(
        name="sOrb",
        condition="FLAG_COND_NONE",
        value="0x0",
        flag="FLAG_OBTAINED_ORB",
        script="SCRIPT_ID(VISIBLE_ITEMS, 3)",
    )
    objects = giratina + orb
    table = """static const DistWorldObjectEvent *sRoom[] = {\n    &sGiratina,\n    &sOrb,\n    NULL\n};
static const DistWorldMapObjectEvents sMapObjectEvents[] = {
    { MAP_HEADER_ROOM, sRoom },
    { MAP_HEADER_INVALID, NULL }
};
"""
    giratina, orb = read_distortion_objects(_distortion(tmp_path, objects, table))
    assert (giratina.header, giratina.script, giratina.x, giratina.z, giratina.y) == (
        "MAP_HEADER_ROOM",
        5,
        15,
        13,
        65536,
    )
    assert (giratina.conditions, giratina.hidden_flag) == ((Condition("var:16469", "=", 13),), None)
    assert (orb.flag_condition, orb.conditions, orb.script, orb.hidden_flag) == ("FLAG_COND_NONE", (), 7003, 1000)


def test_distortion_table_without_end_or_unknown_progress_stops(tmp_path: Path) -> None:
    objects = _OBJECT.format(
        name="sA", condition="FLAG_COND_WORLD_PROGRESS_GEQ", value="UNKNOWN_STEP", flag="0", script="1"
    )
    table = "static const DistWorldObjectEvent *sRoom[] = {\n    &sA,\n    NULL\n};\n"
    ended = "static const DistWorldMapObjectEvents sMapObjectEvents[] = {\n    { MAP_HEADER_ROOM, sRoom },\n"
    repo = _distortion(tmp_path, objects, table + ended + "};\n")
    with pytest.raises(ValueError, match="sans fin"):
        read_distortion_objects(repo)
    source = tmp_path / "src/overlay009/ov9_02249960.c"
    source.write_text(objects + table + ended + "    { MAP_HEADER_INVALID, NULL }\n};\n", encoding="utf-8")
    with pytest.raises(ValueError, match="étape du Monde Distorsion inconnue"):
        read_distortion_objects(repo)


def test_included_defines_follow_constants_headers(tmp_path: Path) -> None:
    (tmp_path / "asm").mkdir()
    (tmp_path / "include/constants").mkdir(parents=True)
    (tmp_path / "asm/scrcmd.inc").write_text('#include "constants/scrcmd.h"\n#define LOCAL_ONLY 4\n', encoding="utf-8")
    (tmp_path / "include/constants/scrcmd.h").write_text(
        '#include "constants/menu.h"\n#include "generated/other.h"\n#define LOCALID 0xF1\n#define TWICE 1\n'
        "#define EXPRESSION (A + 1)\n",
        encoding="utf-8",
    )
    (tmp_path / "include/constants/menu.h").write_text(
        "#define MENU_NO             1 // non\n#define MENU_NOTHING -1\n#define TWICE 2\n", encoding="utf-8"
    )
    found = included_defines(tmp_path, ("asm/scrcmd.inc",))
    assert found == {"LOCAL_ONLY": 4, "LOCALID": 0xF1, "MENU_NO": 1, "MENU_NOTHING": -1}
