"""Lecture complète des deux dépôts DS épinglés et comparaisons Diamant/Perle ↔ Platine (tests `pipeline`)."""

import re
from collections import defaultdict
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import DIAMOND_PEARL, PLATINUM
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_gen4_gx import primitives
from pokemaps_data.pret_gen4_land import read_land_block
from pokemaps_data.pret_gen4_map_models import EMPTY_BLOCK
from pokemaps_data.pret_gen4_narc import members
from pokemaps_data.pret_gen4_nitro import read_nsbmd
from pokemaps_data.pret_gen4_script_binary import ScriptFile
from pokemaps_data.pret_gen4_scripts import TextScriptFile
from pokemaps_data.pret_gen4_textures import decode, read_nsbtx
from pokemaps_data.sources import pret_dir

CACHE = Path(__file__).resolve().parent.parent / ".cache"
# MAP_HEADER_DYNAMIC : ascenseurs et passages dont la destination est choisie par script (phase 3).
DYNAMIC_HEADER = 4095
# Blocs de Diamant/Perle au BDHC tronqué, utilisés seulement par des matrices qu'aucun en-tête ne désigne.
TRUNCATED_DP_BLOCKS = frozenset({422, 423, 424, 425, 426, 427, 428, 429, 430, 453})
# Commandes de script de même numéro mais d'arguments différents entre les deux jeux (relu dans les deux
# sources) : étage d'ascenseur, premier combat, commande 1E1, Poffin et commandes de texte réorganisées.
DIFFERENT_SCRIPT_COMMANDS = frozenset({0x11D, 0x125, 0x1E1, 0x289, *range(0x2C4, 0x2D1)})


@pytest.fixture(scope="session")
def platinum(source_cache_ready: None) -> Gen4PretRepo:
    return Gen4PretRepo(pret_dir(CACHE, PLATINUM.pret_repo), PLATINUM.pret_versions)


@pytest.fixture(scope="session")
def diamond_pearl(source_cache_ready: None) -> Gen4PretRepo:
    return Gen4PretRepo(pret_dir(CACHE, DIAMOND_PEARL.pret_repo), DIAMOND_PEARL.pret_versions)


def test_counts_of_both_repositories(platinum: Gen4PretRepo, diamond_pearl: Gen4PretRepo) -> None:
    def counts(repo: Gen4PretRepo) -> tuple:
        return (
            len(repo.headers),
            len(repo.matrices),
            len(repo.events),
            len(repo.areas),
            len(repo.prop_sets),
            len(repo.lighting),
            len(repo.cameras),
            {version: len(tables) for version, tables in repo.encounters.items()},
            len(repo.moves),
            len(repo.scripts),
        )

    assert counts(platinum) == (593, 289, 534, 75, 71, 4, 17, {"platinum": 183}, 467, 1124)
    assert counts(diamond_pearl) == (559, 245, 512, 59, 55, 3, 16, {"diamond": 183, "pearl": 183}, 467, 538)
    assert len(diamond_pearl.init_scripts) == 512 and len(platinum.frontier_scripts) == 9


@pytest.mark.parametrize("variant", ["platinum", "diamond_pearl"])
def test_headers_designate_existing_files_and_warps(
    variant: str, request: pytest.FixtureRequest, source_cache_ready: None
) -> None:
    repo: Gen4PretRepo = request.getfixturevalue(variant)
    dynamic = 0
    for header in repo.headers.values():
        assert header.matrix in repo.matrices and header.area in repo.areas and header.scripts in repo.scripts
        assert all(table in repo.encounters[version] for version, table in header.encounters)
        matrix, events = repo.matrices[header.matrix], repo.events[header.events]
        for warp in events.warp_events:
            if warp.destination_header == DYNAMIC_HEADER:
                dynamic += 1
                continue
            destination = repo.events[repo.headers[warp.destination_header].events]
            assert warp.destination_warp < len(destination.warp_events)
        for event in events.object_events:
            assert 0 <= event.x < matrix.width * 32 and 0 <= event.z < matrix.height * 32
    assert dynamic == 6
    if not repo.platinum:
        assert {header.init_scripts for header in repo.headers.values()} <= repo.init_scripts.keys()


def _used_blocks(repo: Gen4PretRepo) -> set[int]:
    used = {header.matrix for header in repo.headers.values()}
    return {block for index in used for row in repo.matrices[index].blocks for block in row if block != EMPTY_BLOCK}


def test_every_block_reads_except_unused_truncated_ones(platinum: Gen4PretRepo, diamond_pearl: Gen4PretRepo) -> None:
    for path in sorted((platinum.root / "res/field/maps/data").glob("map_data_*.bin")):
        read_land_block(path, diamond_pearl=False)
    failures = set()
    for index, path in members(diamond_pearl.root / "files/fielddata/land_data/land_data_release").items():
        try:
            read_land_block(path, diamond_pearl=True)
        except ValueError as error:
            assert "BDHC tronqué" in str(error)
            failures.add(index)
    assert failures == TRUNCATED_DP_BLOCKS
    assert not failures & _used_blocks(diamond_pearl)


@pytest.mark.parametrize("variant", ["platinum", "diamond_pearl"])
def test_used_blocks_models_and_bound_textures_decode(
    variant: str, request: pytest.FixtureRequest, source_cache_ready: None
) -> None:
    repo: Gen4PretRepo = request.getfixturevalue(variant)
    texture_sets = defaultdict(set)
    for header in repo.headers.values():
        matrix = repo.matrices[header.matrix]
        for row in matrix.blocks:
            for block in row:
                if block != EMPTY_BLOCK:
                    texture_sets[block].add(repo.areas[header.area].texture_set)
    decoded = set()
    for block, sets in sorted(texture_sets.items()):
        model = read_nsbmd(repo.land_block(block).model, f"bloc {block}")
        for shape in (shape for m in model.models for shape in m.shapes):
            primitives(shape.display_list, f"bloc {block} {shape.name}")
        for texture_set in sets:
            textures = repo.map_textures(texture_set)
            for material in (material for m in model.models for material in m.materials):
                key = (texture_set, material.texture, material.palette)
                # Les liaisons absentes du jeu de textures d'une zone sont résolues avec les en-têtes en phase 3.
                bound = material.texture in textures.textures and material.palette in textures.palettes
                if bound and key not in decoded:
                    decode(textures.textures[material.texture], textures.palettes[material.palette])
                    decoded.add(key)
    assert len(decoded) > 1000


@pytest.mark.parametrize("variant", ["platinum", "diamond_pearl"])
def test_prop_models_and_texture_sets_read(
    variant: str, request: pytest.FixtureRequest, source_cache_ready: None
) -> None:
    repo: Gen4PretRepo = request.getfixturevalue(variant)
    for index, models in repo.prop_sets.items():
        repo.prop_textures(index)
        for model in set(models):
            for shape in (shape for m in repo.prop_model(model).models for shape in m.shapes):
                primitives(shape.display_list, f"objet {model}")
    for area in repo.areas.values():
        repo.map_textures(area.texture_set)


def test_diamond_pearl_character_textures_read(diamond_pearl: Gen4PretRepo) -> None:
    for path in members(diamond_pearl.root / "files/data/mmodel/mmodel").values():
        data = path.read_bytes()
        if data[:4] == b"BTX0":
            read_nsbtx(data, str(path))
        elif data[:4] == b"BMD0":
            read_nsbmd(data, str(path))


def test_engine_tables_are_shared_by_both_games(platinum: Gen4PretRepo, diamond_pearl: Gen4PretRepo) -> None:
    assert platinum.cameras[:16] == diamond_pearl.cameras
    assert platinum.lighting[0] == diamond_pearl.lighting[0] and platinum.lighting[1] == diamond_pearl.lighting[1]
    assert platinum.lighting[2] != diamond_pearl.lighting[2]
    sinnoh = zip(platinum.matrices[0].blocks, diamond_pearl.matrices[0].blocks, strict=True)
    assert sum(a == b for row_a, row_b in sinnoh for a, b in zip(row_a, row_b, strict=True)) == 877
    platinum_attributes = {platinum.land_block(index).attributes for index in range(666)}
    same_index = shared = 0
    for index in members(diamond_pearl.root / "files/fielddata/land_data/land_data_release"):
        if index in TRUNCATED_DP_BLOCKS:
            continue
        attributes = diamond_pearl.land_block(index).attributes
        same_index += attributes == platinum.land_block(index).attributes
        shared += attributes in platinum_attributes
    assert (same_index, shared) == (158, 483)


def test_moves_have_the_same_effect_numbers_in_both_games(platinum: Gen4PretRepo, diamond_pearl: Gen4PretRepo) -> None:
    aliases = {"VISEGRIP": "VICEGRIP", "FEINTATTACK": "FAINTATTACK", "HIGHJUMPKICK": "HIJUMPKICK"}
    aliases |= {"SMELLINGSALTS": "SMELLINGSALT"}

    def key(const: str) -> str:
        compact = const.replace("_", "")
        return aliases.get(compact, compact)

    moves = {key(move.const): (move.effect, move.chance_percent, move.pp) for move in platinum.moves}
    assert moves == {key(move.const): (move.effect, move.chance_percent, move.pp) for move in diamond_pearl.moves}


def _platinum_command_layouts(root: Path) -> dict[int, tuple[int, ...]]:
    """Arguments des macros de Platine formées d'un seul opcode suivi de données (.short, .byte, .long)."""
    ids = re.findall(r"ScriptCommand\((SCRCMD_\w+),", (root / "include/data/scripts/scrcmd.h").read_text("utf-8"))
    opcodes = {name: index for index, name in enumerate(ids)}
    sizes = {"short": 2, "byte": 1, "long": 4}
    layouts: dict[int, set[tuple[int, ...]]] = defaultdict(set)
    text = (root / "asm/macros/scrcmd.inc").read_text("utf-8")
    for body in re.findall(r"^\s*\.macro\s+\w+[^\n]*\n(.*?)^\s*\.endm", text, re.MULTILINE | re.DOTALL):
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        first = re.match(r"^\.short (SCRCMD_\w+)$", lines[0]) if lines else None
        data = [re.match(r"^\.(short|byte|long)\s+(.*)$", line) for line in lines[1:]]
        if first and all(data):
            layout = tuple(sizes[d.group(1)] for d in data if d for _ in d.group(2).split(","))
            layouts[opcodes[first.group(1)]].add(layout)
    return {opcode: next(iter(found)) for opcode, found in layouts.items() if len(found) == 1}


def test_diamond_pearl_command_layouts_match_platinum_macros(
    platinum: Gen4PretRepo, diamond_pearl: Gen4PretRepo
) -> None:
    compared, different = 0, set()
    for opcode, layout in _platinum_command_layouts(platinum.root).items():
        command = diamond_pearl.script_commands[opcode] if opcode < 721 else None
        if command is None or command.cases:
            continue
        compared += 1
        if tuple(argument.size for argument in command.arguments) != layout:
            different.add(opcode)
    assert compared == 711 and different == DIFFERENT_SCRIPT_COMMANDS


def test_diamond_pearl_scripts_decode_including_giratina(diamond_pearl: Gen4PretRepo) -> None:
    giratina = diamond_pearl.scripts[283]
    assert isinstance(giratina, ScriptFile)
    battle = giratina.instructions[93]
    assert (battle.name, battle.arguments) == ("ScrCmd_LegendaryBattle", (487, 70))
    instructions = sum(len(f.instructions) for f in diamond_pearl.scripts.values() if isinstance(f, ScriptFile))
    assert instructions == 41_187


def test_platinum_scripts_use_known_macros(platinum: Gen4PretRepo) -> None:
    twinleaf = platinum.scripts[platinum.names.archives["scripts"]["scripts_twinleaf_town"]]
    assert twinleaf.entries[0] == "TwinleafTown_OnTransition"
    files = [f for f in platinum.scripts.values() if isinstance(f, TextScriptFile)]
    assert len(files) == 1124
    assert sum(len(calls) for f in files for calls in f.labels.values()) > 50_000


def test_ds_move_effects_have_french_texts(gen4_builder: DatabaseBuilder) -> None:
    rows = gen4_builder.moves.move_version_group_table()
    assert len(rows) == 932 and all(row[7].strip() for row in rows)
    thunder_punch = next(row for row in rows if row[0] == 9 and row[1] == gen4_builder.vg_ids[0])
    assert thunder_punch[7:] == ("Inflige des dégâts et peut paralyser la cible.", 10)
