"""Table des commandes de Diamant/Perle, désassemblage et scripts texte de Platine, sur des sources construites
dans le test (sans cache ni réseau)."""

import struct
from pathlib import Path

import pytest

from pokemaps_data.pret_gen4_script_binary import Instruction, _check_overlaps, read_init_scripts, read_script_file
from pokemaps_data.pret_gen4_script_commands import read_command_table
from pokemaps_data.pret_gen4_scripts import read_macros, read_text_script

# Commandes du moteur factice, par opcode.
NAMES = [
    "ScrCmd_Nop",
    "ScrCmd_Message",
    "ScrCmd_End",
    "ScrCmd_GoTo",
    "ScrCmd_GoToIf",
    "ScrCmd_Movement",
    "ScrCmd_Option",
    "ScrCmd_Poffin",
    "ScrCmd_Maybe",
    "ScrCmd_Helper",
    "ScrCmd_AsmLinear",
    "ScrCmd_AsmTable",
    "ScrCmd_AsmCompare",
    "ScrCmd_AsmBytes",
]

C_SOURCE = """
BOOL ScrCmd_Nop(ScriptContext *ctx) { return FALSE; }
BOOL ScrCmd_Message(ScriptContext *ctx) { // message
    u8 id = ScriptReadByte(ctx);
    return FALSE;
}
BOOL ScrCmd_End(ScriptContext *ctx) { StopScript(ctx); return FALSE; }
BOOL ScrCmd_GoTo(ScriptContext *ctx) {
    s32 offset = (s32)ScriptReadWord(ctx);
    ScriptJump(ctx, ctx->scriptPtr + offset);
    return FALSE;
}
BOOL ScrCmd_GoToIf(ScriptContext *ctx) {
    u8 type = ScriptReadByte(ctx);
    s32 offset = (s32)ScriptReadWord(ctx);
    if (type == ctx->comparisonResult) {
        ScriptJump(ctx, ctx->scriptPtr + offset);
    }
    return FALSE;
}
BOOL ScrCmd_Movement(ScriptContext *ctx) {
    u16 object = ScriptGetVar(ctx);
    u32 offset = ScriptReadWord(ctx);
    Move(object, ctx->scriptPtr + offset);
    return FALSE;
}
BOOL ScrCmd_Option(ScriptContext *ctx) {
    u8 option = ScriptReadByte(ctx);
    switch (option) {
    case 0:
        break;
    case 2: {
        u16 *ret = ScriptGetVarPointer(ctx);
        break;
    }
    default:
        break;
    }
    return FALSE;
}
BOOL ScrCmd_Poffin(ScriptContext *ctx) {
    u16 *var = ScriptGetVarPointer(ctx);
    u8 bytes[3];
    for (s32 i = 0; i < 3; i++) {
        bytes[i] = ScriptReadByte(ctx);
    }
    u8 last = ScriptReadByte(ctx);
    return FALSE;
}
BOOL ScrCmd_Maybe(ScriptContext *ctx) {
    if (Flag()) {
        u16 value = ScriptReadHalfword(ctx);
    }
    return FALSE;
}
static void ReadPair(ScriptContext *ctx) {
    u16 a = ScriptReadHalfword(ctx);
    u16 b = ScriptGetVar(ctx);
}
BOOL ScrCmd_Helper(ScriptContext *ctx) {
    ReadPair(ctx);
    unused(ctx);
    return FALSE;
}
"""

ASM_SOURCE = """\tthumb_func_start ScrCmd_AsmLinear
ScrCmd_AsmLinear:
\tpush {r4, lr}
\tadd r4, r0, #0x0
\tbl ScriptReadHalfword
\tbl ScriptReadWord
\tpop {r4, pc}
\tthumb_func_start ScrCmd_AsmTable
ScrCmd_AsmTable:
\tpush {r4, lr}
\tadd r4, r0, #0x0
\tbl ScriptReadHalfword
\tcmp r0, #0x1
\tbls _0
\tb _end
_0:
\tadd pc, r0
_table: ; jump table (using 16-bit offset)
\t.short _a - _table - 2; case 0
\t.short _b - _table - 2; case 1
_a:
\tb _end
_b:
\tbl ScriptReadHalfword
\tbl ScriptReadHalfword
\tbeq _end
\tb _end
_end:
\tpop {r4, pc}
\tthumb_func_start ScrCmd_AsmCompare
ScrCmd_AsmCompare:
\tpush {r4, lr}
\tbl ScriptReadHalfword
\tcmp r0, #0x0
\tbeq _c0
\tb _done
_c0:
\tbl ScriptReadHalfword
_done:
\tpop {r4, pc}
\tthumb_func_start ScrCmd_AsmBytes
ScrCmd_AsmBytes:
\tpush {r3-r7, lr}
\tadd r5, r0, #0x0
\tldr r1, [r5, #0x8]
\tadd r2, r1, #0x1
\tstr r2, [r5, #0x8]
\tldrb r6, [r1, #0x0]
\tpop {r3-r7, pc}
"""


@pytest.fixture()
def engine(tmp_path: Path) -> Path:
    table = [f"\t.word {NAMES[i] if i < len(NAMES) else 'ScrCmd_Nop'}" for i in range(721)]
    asm = tmp_path / "arm9/asm"
    asm.mkdir(parents=True)
    (asm / "unk_02038C78.s").write_text(
        "\t.word 721 ; NELEMS(gScriptCmdTable)\n\t.global gScriptCmdTable\ngScriptCmdTable:\n" + "\n".join(table)
    )
    (asm / "scrcmd_1.s").write_text(ASM_SOURCE)
    (tmp_path / "arm9/src").mkdir()
    (tmp_path / "arm9/src/scrcmd.c").write_text(C_SOURCE)
    return tmp_path


def layout(engine: Path, name: str) -> tuple:
    command = next(c for c in read_command_table(engine) if c.name == name)
    if command.problem:
        return ("illisible", command.problem)
    cases = tuple((value, tuple(a.size for a in extra)) for value, extra in command.cases)
    return tuple((a.size, a.role) for a in command.arguments), cases, command.ends


def test_command_layouts_are_read_from_c_bodies(engine: Path) -> None:
    assert layout(engine, "ScrCmd_End") == ((), (), True)
    assert layout(engine, "ScrCmd_GoTo") == (((4, "jump"),), (), True)
    assert layout(engine, "ScrCmd_GoToIf") == (((1, "value"), (4, "jump")), (), False)
    assert layout(engine, "ScrCmd_Movement") == (((2, "var"), (4, "data")), (), False)
    assert layout(engine, "ScrCmd_Option") == (((1, "value"),), ((0, ()), (2, (2,))), False)
    assert layout(engine, "ScrCmd_Poffin")[0] == ((2, "var"), *([(1, "value")] * 4))
    assert layout(engine, "ScrCmd_Helper") == (((2, "value"), (2, "var")), (), False)
    assert layout(engine, "ScrCmd_Maybe") == ("illisible", "lecture conditionnelle (ScriptReadHalfword)")


def test_command_layouts_are_read_from_assembly(engine: Path) -> None:
    assert layout(engine, "ScrCmd_AsmLinear") == (((2, "value"), (4, "value")), (), False)
    assert layout(engine, "ScrCmd_AsmTable") == (((2, "value"),), ((0, ()), (1, (2, 2))), False)
    assert layout(engine, "ScrCmd_AsmCompare") == (((2, "value"),), ((0, (2,)),), False)
    assert layout(engine, "ScrCmd_AsmBytes") == (((1, "value"),), (), False)


def script(*entries: int, marker: bool = True) -> bytes:
    """Table des entrées vers des décalages absolus, terminée ou non par 0xFD13."""
    words = b"".join(struct.pack("<i", target - (4 * i + 4)) for i, target in enumerate(entries))
    return words + (struct.pack("<H", 0xFD13) if marker else b"")


def test_scripts_follow_branches_movements_and_switches(engine: Path, tmp_path: Path) -> None:
    commands = read_command_table(engine)
    code = bytearray(0x24)
    code[0:6] = script(6)
    struct.pack_into("<HBi", code, 0x06, 4, 1, 0x1A - 0x0D)  # GoToIf vers End
    struct.pack_into("<HHi", code, 0x0D, 5, 0x8000, 0x1C - 0x15)  # Movement : données à 0x1C
    struct.pack_into("<HBH", code, 0x15, 6, 2, 0x800C)  # Option 2 : une variable de plus
    struct.pack_into("<H", code, 0x1A, 2)  # End
    struct.pack_into("<4H", code, 0x1C, 12, 1, 0xFE, 0)
    path = tmp_path / "narc_0001.bin"
    path.write_bytes(bytes(code))
    result = read_script_file(path, commands)
    assert result.entries == (6,)
    names = [result.instructions[offset].name for offset in sorted(result.instructions)]
    assert names == ["ScrCmd_GoToIf", "ScrCmd_Movement", "ScrCmd_Option", "ScrCmd_End"]
    assert result.instructions[0x06].arguments == (1, 0x1A)
    assert result.instructions[0x15].arguments == (2, 0x800C)
    assert result.movements == {0x1C: ((12, 1),)}


def test_code_and_data_may_not_overlap() -> None:
    instructions = {0: Instruction(0, 2, "ScrCmd_End", (), 4)}
    with pytest.raises(ValueError, match="code et données se chevauchent à 0x2"):
        _check_overlaps(instructions, {2: ()}, "scripts")


def test_entry_table_without_marker_and_unreadable_commands(engine: Path, tmp_path: Path) -> None:
    commands = read_command_table(engine)
    path = tmp_path / "narc_0002.bin"
    path.write_bytes(script(8, 10, marker=False) + struct.pack("<HH", 2, 2))
    assert read_script_file(path, commands).entries == (8, 10)
    path.write_bytes(script(6) + struct.pack("<H", 8) + bytes(4))
    with pytest.raises(ValueError, match="ScrCmd_Maybe illisible à 0x6"):
        read_script_file(path, commands)
    path.write_bytes(script(6) + struct.pack("<H", 900))
    with pytest.raises(ValueError, match="commande inconnue 0x0384 à 0x6"):
        read_script_file(path, commands)


def test_init_scripts_with_fixed_entries_and_frame_table(tmp_path: Path) -> None:
    path = tmp_path / "narc_0003.bin"
    table_offset = 11
    data = struct.pack("<BHH", 2, 1, 0) + struct.pack("<Bi", 1, table_offset - 10) + b"\0"
    data += struct.pack("<3H", 0x4001, 3, 4) + struct.pack("<H", 0)
    path.write_bytes(data)
    init = read_init_scripts(path)
    assert init.fixed == ((2, 1),) and init.frame_table == ((0x4001, 3, 4),)
    path.write_bytes(struct.pack("<BHH", 9, 1, 0) + b"\0")
    with pytest.raises(ValueError, match="type d'initialisation inconnu 9"):
        read_init_scripts(path)


def test_platinum_text_scripts_check_macros_and_entries(tmp_path: Path) -> None:
    macros = tmp_path / "asm/macros/scrcmd.inc"
    macros.parent.mkdir(parents=True)
    macros.write_text(
        "    .macro ScriptEntry name\n    .endm\n    .macro ScriptEntryEnd\n    .endm\n"
        "    .macro End\n    .endm\n    .macro SetVar var, value\n    .endm\n"
        "    .macro FadeScreenOut frames = 0, color = 0\n    .endm\n    .macro Need value:req\n    .endm\n"
    )
    definitions = read_macros(tmp_path, ("asm/macros/scrcmd.inc",))
    path = tmp_path / "scripts_town.s"
    path.write_text(
        '#include "macros/scrcmd.inc"\n#define LOCAL VAR_MAP_LOCAL_0x00\n\n    ScriptEntry Town_Start\n'
        "    ScriptEntryEnd\n\nTown_Start: @ commentaire\n    SetVar LOCAL, 1 /* c */\n    FadeScreenOut\n"
        "    End\n\n    .balign 4, 0\n"
    )
    result = read_text_script(path, definitions)
    assert result.entries == ("Town_Start",) and result.defines == {"LOCAL": "VAR_MAP_LOCAL_0x00"}
    assert [call.name for call in result.labels["Town_Start"]] == ["SetVar", "FadeScreenOut", "End", ".balign"]
    path.write_text("Town_Start:\n    SetVar A, 1, 2\n")
    with pytest.raises(ValueError, match="SetVar attend 0 à 2 arguments"):
        read_text_script(path, definitions)
    path.write_text("Town_Start:\n    Need\n")
    with pytest.raises(ValueError, match="Need attend 1 à 1 arguments"):
        read_text_script(path, definitions)
    path.write_text("    ScriptEntry Missing\n    ScriptEntryEnd\n")
    with pytest.raises(ValueError, match="points d'entrée sans label"):
        read_text_script(path, definitions)
