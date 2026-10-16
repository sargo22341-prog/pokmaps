"""Règles sauvages du moteur de Diamant/Perle, lues dans l'assembleur Thumb de pokediamond (overlays 05 et 06, arm9).

Le moteur sauvage n'y est pas décompilé : chaque fonction est désignée par son étiquette (adresse dans la ROM
américaine) et sa forme est vérifiée instruction par instruction avant d'en tirer une valeur. Les fonctions sont
les équivalents compilés de celles de Platine (wild_encounters.c, map_tile_behavior.c, honey_tree.c…) ; un test
compare les deux lectures.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import asm_data, asm_function, asm_threshold_rates
from .pret_gen4_source import read_text
from .pret_gen4_wild_rules import (
    HONEY_SLOTS,
    LAND_SLOTS,
    RODS,
    WATER_SLOTS,
    HoneyRules,
    Replacements,
    SlotRates,
    TileRules,
    WildRules,
)

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

_FIELD = "arm9/overlays/06/asm/overlay_06.s"
_HONEY = "arm9/overlays/05/asm/ov05_021F4CF8.s"
_TILES = "arm9/asm/unk_0205478C.s"
_ROAMERS = "arm9/asm/unk_020603B0.s"
# Fonction principale des rencontres à pied et au surf (WildEncounters_TryWildEncounter) et ses appels.
_TRY_WILD = "ov06_0223BA04"
_CALLS = {"time": "ov06_0223B944", "swarm": "ov06_0223B970", "daily": "ov06_0223B9A8", "dual_slot": "ov06_0224CDB8"}
# Table des 12 emplacements recopiée sur la pile (8 octets chacun) avant les remplacements.
_TABLE_BASE = 0x54
_SLOT_SIZE = 8
# Opcode du script CreateRoamer (scrcmd.c) et numéros d'errants de Save_CreateRoamerByID.
_CREATE_ROAMER = 0x21C


def read_dp_wild_rules(repo: Gen4PretRepo) -> WildRules:
    field = read_text(repo.root / _FIELD)
    headers = {header.constant: header.index for header in repo.headers.values()}
    return WildRules(
        rates=_rates(field),
        replacements=_replacements(field),
        tiles=_tiles(read_text(repo.root / _TILES)),
        swarm_headers=_words(asm_data(field, "ov06_02251340", _FIELD), 28, repo),
        honey=_honey(repo, field),
        trophy_garden=_single(repo, "MapHeader_MapIsTrophyGarden", headers),
        great_marsh=_great_marsh(field, headers),
        feebas=(_single(repo, "MapHeader_MapIsMtCoronetFeebasRoom", headers), _feebas_levels(field)),
        roamer_headers=_roamer_headers(repo, headers),
        roamers=_roamers(repo),
        unown_forms=_unown_forms(field),
    )


def _rates(field: str) -> SlotRates:
    land = asm_threshold_rates(asm_function(field, "ov06_0223C5AC", _FIELD), "r0", LAND_SLOTS, "herbe")
    surf = asm_threshold_rates(asm_function(field, "ov06_0223C648", _FIELD), "r0", WATER_SLOTS, "surf")
    lines = asm_function(field, "ov06_0223C694", _FIELD)
    rods = []
    for index, rod in enumerate(RODS):
        branch = f"cmp r5, #{index}"
        if branch not in lines or not lines[lines.index(branch) + 1].startswith("beq "):
            raise ValueError(f"{_FIELD} : aiguillage de la canne {rod} introuvable")
        label = lines[lines.index(branch) + 1].split()[1]
        start = lines.index(f"{label}:")
        end = lines.index("mov r4, #4", start)
        rods.append((rod, asm_threshold_rates(lines[start : end + 1], "r0", WATER_SLOTS, rod)))
    return SlotRates(land, surf, tuple(rods))


def _replacements(field: str) -> Replacements:
    lines = asm_function(field, _TRY_WILD, _FIELD)
    copy = lines.index(f"add r2, sp, #{_TABLE_BASE:#x}")
    if "cmp r0, #0xc" not in lines[copy : copy + 15]:
        raise ValueError(f"{_FIELD} : copie des 12 emplacements d'herbe introuvable")

    def slots(function: str) -> tuple[int, ...]:
        calls = [index for index, line in enumerate(lines) if line == f"bl {function}"]
        if len(calls) != 1:
            raise ValueError(f"{_FIELD} : appel de {function} introuvable ou répété")
        offsets = [
            int(found, 16)
            for line in lines[calls[0] - 3 : calls[0]]
            for found in re.findall(r"sp, #(0x[0-9a-f]+)", line)
        ]
        if len(offsets) != 2:
            raise ValueError(f"{_FIELD} : emplacements passés à {function} illisibles")
        return tuple((offset - _TABLE_BASE) // _SLOT_SIZE for offset in offsets)

    _check_time_of_day(asm_function(field, _CALLS["time"], _FIELD))
    radar = asm_function(field, "ov06_0223C31C", _FIELD)
    stored = [int(value, 16) for line in radar[:30] for value in re.findall(r"str r0, \[r4, #(0x[0-9a-f]+)\]", line)]
    marsh = asm_function(field, "ov06_0223CFFC", _FIELD)
    daily = sorted(int(value, 16) for line in marsh for value in re.findall(r"add r[14], #(0x[0-9a-f]+)", line))
    marsh_slots = tuple(offset // _SLOT_SIZE for offset in daily)
    if len(stored) != 4 or slots(_CALLS["daily"]) != marsh_slots:
        raise ValueError(f"{_FIELD} : emplacements du Pokéradar ou du tirage quotidien illisibles")
    return Replacements(
        swarm=slots(_CALLS["swarm"]),
        time=slots(_CALLS["time"]),
        radar=tuple(offset // _SLOT_SIZE for offset in stored),
        daily=marsh_slots,
        dual_slot=slots(_CALLS["dual_slot"]),
    )


def _check_time_of_day(lines: list[str]) -> None:
    """Heures 1 et 2 (jour, crépuscule) : champs 0x6c/0x70 ; heures 3 et 4 (nuit) : 0x74/0x78 ; matin inchangé."""
    expected = [
        "bl GF_RTC_GetTimeOfDay",
        "sub r1, r0, #1",
        "cmp r1, #1",
        "ldr r0, [r5, #0x6c]",
        "ldr r0, [r5, #0x70]",
        "sub r0, r0, #3",
        "cmp r0, #1",
        "ldr r0, [r5, #0x74]",
        "ldr r0, [r5, #0x78]",
    ]
    positions = [lines.index(line) if line in lines else -1 for line in expected]
    if -1 in positions or positions != sorted(positions):
        raise ValueError(f"{_FIELD} : règle des moments de la journée inconnue")


def _tiles(text: str) -> TileRules:
    flags = asm_data(text, "UNK_020F5C14", _TILES)
    surf = asm_function(text, "sub_0205481C", _TILES)
    encounter = asm_function(text, "sub_02054AFC", _TILES)
    if "mov r0, #0x1" not in surf or "mov r0, #0x2" not in encounter or len(flags) != 256:
        raise ValueError(f"{_TILES} : drapeaux de comportement inconnus")

    def tested(label: str) -> frozenset[int]:
        values = {
            int(value, 16)
            for line in asm_function(text, label, _TILES)
            for value in re.findall(r"cmp r0, #(0x[0-9a-f]+)", line)
        }
        if not values:
            raise ValueError(f"{_TILES} : {label} illisible")
        return frozenset(values)

    # Prédicats IsTallGrass, IsVeryTallGrass et IsMudWithGrass, dans l'ordre de map_tile_behavior.c de Platine.
    tall = tested("sub_0205478C")
    grass = tall | tested("sub_02054798") | tested("sub_02054990")
    if len(tall) != 1:
        raise ValueError(f"{_TILES} : un seul comportement d'herbes hautes attendu")
    return TileRules(tuple(flags), next(iter(tall)), grass)


def _words(data: bytes, count: int, repo: Gen4PretRepo) -> tuple[int, ...]:
    values = tuple(int.from_bytes(data[index : index + 4], "little") for index in range(0, len(data), 4))
    if len(values) != count or len(data) != 4 * count or any(value not in repo.headers for value in values):
        raise ValueError(f"{repo.root} : table de {count} en-têtes attendue, lu {values}")
    return values


def _honey(repo: Gen4PretRepo, field: str) -> HoneyRules:
    text = read_text(repo.root / _HONEY)
    tables = re.search(
        r"ov05_021FC644:[^\n]*\n\.ifdef DIAMOND\n\s*\.word ([\d, ]+)\n\.else\n\s*\.word ([\d, ]+)\n\.endif", text
    )
    if tables is None:
        raise ValueError(f"{_HONEY} : tables des arbres à Miel par version illisibles")
    versions = tuple(
        (version, tuple(int(v) for v in values.split(",")))
        for version, values in zip(("diamond", "pearl"), tables.groups(), strict=True)
    )
    groups = asm_function(text, "ov05_021F4EE4", _HONEY)
    split = groups.index("_021F4F2A:")
    shake = asm_function(text, "ov05_021F5068", _HONEY)
    model = shake.index("bl ov05_021E7ED8") if "bl ov05_021E7ED8" in shake else 0
    found = re.fullmatch(r"mov r1, #(0x[0-9a-f]+)", shake[model - 1]) if model else None
    level = asm_function(field, "ov06_0223CCDC", _FIELD)
    if found is None or not {"cmp r6, #0xb", "add r0, r6, #5", "mov r7, #0xf"} <= set(level):
        raise ValueError(f"{_FIELD} : niveaux des arbres à Miel illisibles")
    return HoneyRules(
        headers=_words(asm_data(text, "ov05_021FC650", _HONEY), 21, repo),
        tables=tuple((version, (values[0], values[1], values[2])) for version, values in versions),
        slot_rates=_asm_values(asm_function(text, "ov05_021F4F44", _HONEY), "r5", HONEY_SLOTS),
        levels=(5, 15),
        normal_groups=_asm_groups(groups[split:]),
        munchlax_groups=_asm_groups(groups[:split]),
        model=int(found.group(1), 16),
    )


def _unown_forms(field: str) -> tuple[tuple[int, ...], ...]:
    """Groupes de formes de Zarbi : nombre (mot) puis adresse de la liste, huit fois ; formes de Sancoki et Tritosor
    selon les octets 0xf et 0x10 des paramètres de rencontre, comme dans Platine."""
    count = int.from_bytes(asm_data(field, "ov06_0224F308", _FIELD), "little")
    match = re.search(r"ov06_0224F30C:[^\n]*\n((?:\s*\.word[^\n]*\n)+)", field)
    lines = match.group(1).splitlines() if match else []
    words = [word.strip() for line in lines for word in line.split(".word")[1].split(",")]
    party = set(asm_function(field, "ov06_0223D1BC", _FIELD))
    if len(words) % 2 != 1 or not {"ldrb r0, [r5, #0xf]", "ldrb r0, [r5, #0x10]", "cmp r0, #0xc9"} <= party:
        raise ValueError(f"{_FIELD} : formes sauvages de Diamant/Perle illisibles")
    groups = []
    counts = [count, *(int(value, 0) for value in words[1::2])]
    for label, size in zip(words[0::2], counts, strict=True):
        data = asm_data(field, label, _FIELD)
        groups.append(tuple(data[:size]))
    if any(len(group) != size for group, size in zip(groups, counts, strict=True)):
        raise ValueError(f"{_FIELD} : groupes de formes de Zarbi incomplets")
    return tuple(groups)


def _asm_values(lines: list[str], register: str, count: int) -> tuple[int, ...]:
    """Valeurs (`mov r0, #V`) choisies par une suite `cmp REG, #N` / `bge`, la dernière prenant le reste."""
    rates = [0] * count
    low = 0
    stores = {"strb r0, [r4]", "strb r0, [r5]"}
    for index, line in enumerate(lines[:-1]):
        if not line.startswith("mov r0, #") or lines[index + 1] not in stores:
            continue
        bound = 100
        if index >= 2 and (found := re.fullmatch(rf"cmp {register}, #(0x[0-9a-f]+|\d+)", lines[index - 2])):
            bound = int(found.group(1), 0)
        value = int(line.split("#")[1], 0)
        if bound <= low or not 0 <= value < count:
            raise ValueError(f"{_HONEY} : tirage incohérent à « {line} »")
        rates[value] += bound - low
        low = bound
    if low != 100:
        raise ValueError(f"{_HONEY} : tirage incomplet : {rates}")
    return tuple(rates)


def _asm_groups(lines: list[str]) -> tuple[int, int, int, int]:
    rates = _asm_values(lines, "r4", 4)
    return rates[0], rates[1], rates[2], rates[3]


def _single(repo: Gen4PretRepo, function: str, headers: dict[str, int]) -> int:
    text = read_text(repo.root / "arm9/src/map_header.c")
    match = re.search(rf"BOOL {function}\(u32 mapno\) \{{\s*return mapno == (MAP_\w+);\s*\}}", text)
    if match is None or match.group(1) not in headers:
        raise ValueError(f"map_header.c : {function} illisible")
    return headers[match.group(1)]


def _great_marsh(field: str, headers: dict[str, int]) -> tuple[int, ...]:
    """Zone du Grand Marais d'après l'en-tête (ov06_022456A4) et listes quotidiennes selon le Pokédex National."""
    replace = asm_function(field, "ov06_02245658", _FIELD)
    if not {"mov r1, #9", "mov r1, #0xa", "mov r2, #0x1f"} <= set(replace):
        raise ValueError(f"{_FIELD} : tirage quotidien du Grand Marais inconnu")
    names = [f"MAP_GREAT_MARSH_AREA_{number}" for number in range(1, 7)]
    area = asm_function(field, "ov06_022456A4", _FIELD)
    first = [int(value, 16) for line in area[:2] for value in re.findall(r"mov r1, #(0x[0-9a-f]+)", line)]
    if any(name not in headers for name in names) or not first or (first[0] << 2) != headers[names[0]]:
        raise ValueError(f"{_FIELD} : zones du Grand Marais illisibles")
    return tuple(headers[name] for name in names)


def _feebas_levels(field: str) -> tuple[int, int]:
    match = re.search(
        r"\nov06_0224[0-9A-F]+:[^\n]*\n\s*mov r2, #0x14\n\s*strb r2, \[r0\]\n\s*mov r0, #0xa\n\s*strb r0, \[r1\]", field
    )
    if match is None:
        raise ValueError(f"{_FIELD} : niveaux de Barpau illisibles")
    return 10, 20


def _roamer_headers(repo: Gen4PretRepo, headers: dict[str, int]) -> tuple[int, ...]:
    text = read_text(repo.root / _ROAMERS)
    match = re.search(r"UNK_020F7460:[^\n]*\n((?:\s*\.word MAP_\w+\n)+)", text)
    names = re.findall(r"\.word (MAP_\w+)", match.group(1)) if match else []
    if len(names) != 29 or any(name not in headers for name in names):
        raise ValueError(f"{_ROAMERS} : routes des errants illisibles")
    return tuple(headers[name] for name in names)


def _roamers(repo: Gen4PretRepo) -> tuple[tuple[int, int], ...]:
    lines = asm_function(read_text(repo.root / _ROAMERS), "Save_CreateRoamerByID", _ROAMERS)
    table = {0: (0x1E1, 0x32), 1: (0x7A << 2, 0x32), 2: (0x1EB, 0x28)}
    expected = ["ldr r7, _02060580", "mov r6, #0x32", "mov r7, #0x7a", "lsl r7, r7, #0x2", "ldr r7, _02060584"]
    if not all(any(line.startswith(prefix) for line in lines) for prefix in expected) or "mov r6, #0x28" not in lines:
        raise ValueError(f"{_ROAMERS} : errants de Save_CreateRoamerByID illisibles")
    created = sorted(
        {
            instruction.arguments[0]
            for script in repo.scripts.values()
            for instruction in script.instructions.values()
            if instruction.opcode == _CREATE_ROAMER
        }
    )
    if not created or any(slot not in table for slot in created):
        raise ValueError(f"{repo.root} : errants créés par les scripts inconnus : {created}")
    return tuple(table[slot] for slot in created)
