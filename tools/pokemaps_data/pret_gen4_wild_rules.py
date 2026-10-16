"""Règles sauvages du moteur DS, lues dans les sources C de Platine (et, par pret_gen4_wild_rules_dp.py, dans
l'assembleur de Diamant/Perle) : probabilités des emplacements, emplacements remplacés (heure, essaim, Pokéradar,
tirage quotidien, double insertion), comportements des cases, lieux d'essaim, arbres à Miel, errants.

Les deux lecteurs rendent le même modèle ; un test compare ce qui doit être commun.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from .pret_gen4_engine_text import c_function, c_initializer, c_threshold_rates
from .pret_gen4_source import c_enum, metang_enum, read_text

if TYPE_CHECKING:
    from .pret_gen4 import Gen4PretRepo

LAND_SLOTS = 12
WATER_SLOTS = 5
HONEY_SLOTS = 6
RODS = ("old-rod", "good-rod", "super-rod")
GBA_GAMES = ("ruby", "sapphire", "emerald", "firered", "leafgreen")


@dataclass(frozen=True)
class SlotRates:
    land: tuple[int, ...]
    surf: tuple[int, ...]
    rods: tuple[tuple[str, tuple[int, ...]], ...]

    def __post_init__(self) -> None:
        if len(self.land) != LAND_SLOTS or len(self.surf) != WATER_SLOTS or [r for r, _ in self.rods] != list(RODS):
            raise ValueError(f"probabilités sauvages DS invalides : {self}")


@dataclass(frozen=True)
class Replacements:
    """Emplacements d'herbe remplacés (indices de 0 à 11) par chaque mécanisme du moteur."""

    swarm: tuple[int, ...]
    time: tuple[int, ...]
    radar: tuple[int, ...]
    daily: tuple[int, ...]  # Jardin Trophée et Grand Marais
    dual_slot: tuple[int, ...]

    def __post_init__(self) -> None:
        used = [*self.swarm, *self.time, *self.radar, *self.daily, *self.dual_slot]
        if len(set(used)) != len(used) or not set(used) <= set(range(LAND_SLOTS)):
            raise ValueError(f"emplacements remplacés DS incohérents : {self}")


@dataclass(frozen=True)
class TileRules:
    """Comportements des cases : rencontre (herbe, sol ou eau selon le drapeau surf) et herbes."""

    flags: tuple[int, ...]  # 256 valeurs : bit 0 = surf, bit 1 = rencontre
    tall_grass: int  # seul comportement où le Pokéradar s'utilise (TileBehavior_IsTallGrass)
    grass: frozenset[int]  # hautes herbes, très hautes herbes, boue herbeuse

    def __post_init__(self) -> None:
        if len(self.flags) != 256 or self.tall_grass not in self.grass or not self.grass <= self.encounter:
            raise ValueError("comportements de cases DS incohérents")

    @cached_property
    def encounter(self) -> frozenset[int]:
        return frozenset(value for value, flag in enumerate(self.flags) if flag & 2)

    @cached_property
    def surfable(self) -> frozenset[int]:
        return frozenset(value for value, flag in enumerate(self.flags) if flag & 1)


@dataclass(frozen=True)
class HoneyRules:
    headers: tuple[int, ...]  # 21 en-têtes, dans l'ordre des arbres
    tables: tuple[tuple[str, tuple[int, int, int]], ...]  # version -> membres encdata_ex des groupes A, B, C
    slot_rates: tuple[int, ...]  # emplacements 0 à 5
    levels: tuple[int, int]
    normal_groups: tuple[int, int, int, int]  # aucun Pokémon, A, B, C (sur 100)
    munchlax_groups: tuple[int, int, int, int]
    model: int  # modèle d'objet posé de l'arbre (honey_tree.nsbmd)


@dataclass(frozen=True)
class WildRules:
    rates: SlotRates
    replacements: Replacements
    tiles: TileRules
    swarm_headers: tuple[int, ...]
    honey: HoneyRules
    trophy_garden: int
    great_marsh: tuple[int, ...]  # six zones, dans l'ordre du tirage quotidien
    feebas: tuple[int, tuple[int, int]]  # en-tête, (niveau minimal, maximal)
    roamer_headers: tuple[int, ...]
    roamers: tuple[tuple[int, int], ...]  # (espèce, niveau) des errants activés par les scripts
    # Formes de Zarbi tirées selon le champ unown_table de la table (0 et 1 : premier groupe, n : groupe n - 1).
    unown_forms: tuple[tuple[int, ...], ...]


def read_wild_rules(repo: Gen4PretRepo) -> WildRules:
    if repo.platinum:
        return _platinum_rules(repo)
    from .pret_gen4_wild_rules_dp import read_dp_wild_rules

    return read_dp_wild_rules(repo)


def tile_names(repo: Gen4PretRepo) -> tuple[str, ...]:
    """Noms des 256 comportements de cases, d'après l'énumération de Platine."""
    path = repo.root / "include/constants/field/map_tile_behaviors.h"
    values = c_enum(path, "TileBehavior")
    names = ["" for _ in range(256)]
    for name, value in values.items():
        if 0 <= value < 256:
            names[value] = name
    if "" in names:
        raise ValueError(f"{path} : comportements de cases incomplets")
    return tuple(names)


def _platinum_rules(repo: Gen4PretRepo) -> WildRules:
    wild = read_text(repo.root / "src/overlay006/wild_encounters.c")
    where = "wild_encounters.c"
    headers = {header.constant: header.index for header in repo.headers.values()}
    return WildRules(
        rates=SlotRates(
            land=c_threshold_rates(c_function(wild, "GetGroundEncounterSlot", where), "roll", LAND_SLOTS, where),
            surf=c_threshold_rates(c_function(wild, "GetWaterEncounterSlot", where), "roll", WATER_SLOTS, where),
            rods=_rod_rates(c_function(wild, "GetRodEncounterSlot", where), where),
        ),
        replacements=_replacements(wild, where),
        tiles=_tiles(repo),
        swarm_headers=_header_list(repo, "src/overlay006/swarm.c", "sSwarmMapIdTable", headers),
        honey=_honey(repo, headers),
        trophy_garden=_single_header(repo, "MapHeader_IsTrophyGarden", headers),
        great_marsh=_great_marsh(repo, headers),
        feebas=(_single_header(repo, "MapHeader_HasFeebasTiles", headers), _feebas_levels(repo)),
        roamer_headers=_roamer_headers(repo, headers),
        roamers=_roamers(repo),
        unown_forms=_unown_forms(repo, wild, where),
    )


def _rod_rates(body: str, where: str) -> tuple[tuple[str, tuple[int, ...]], ...]:
    result = []
    for rod, name in zip(RODS, ("OLD", "GOOD", "SUPER"), strict=True):
        match = re.search(rf"case FISHING_TYPE_{name}_ROD:(.*?)break;", body, re.DOTALL)
        if match is None:
            raise ValueError(f"{where} : canne {name} absente de GetRodEncounterSlot")
        result.append((rod, c_threshold_rates(match.group(1), "roll", WATER_SLOTS, f"{where} {rod}")))
    return tuple(result)


def _replacements(wild: str, where: str) -> Replacements:
    body = c_function(wild, "WildEncounters_TryWildEncounter", where)

    def slots(function: str) -> tuple[int, ...]:
        calls = re.findall(rf"{function}\(([^;]*)\);", body)
        if len(calls) != 1:
            raise ValueError(f"{where} : appel de {function} introuvable ou répété")
        return tuple(int(value) for value in re.findall(r"encounterTable\[(\d+)\]\.species", calls[0]))

    radar = c_function(wild, "TryGenerateGrassEncounter_WithRadar", where)
    radar_slots = re.findall(r"encounterTable\[(\d+)\]\.species = encounterData->radarEncounters\[(\d)\]", radar)
    if [int(source) for _, source in radar_slots] != [0, 1, 2, 3]:
        raise ValueError(f"{where} : emplacements du Pokéradar illisibles")
    marsh = c_function(wild, "WildEncounters_ReplaceGreatMarshDailyEncounters", where)
    daily = tuple(int(value) for value in re.findall(r"encTable\[(\d+)\]\.species", marsh))
    if slots("WildEncounters_ReplaceTrophyGardenEncounters") != daily:
        raise ValueError(f"{where} : le Jardin Trophée et le Grand Marais remplacent des emplacements différents")
    _check_time_of_day(repo_text=wild, where=where)
    return Replacements(
        swarm=slots("WildEncounters_ReplaceSwarmEncounters"),
        time=slots("WildEncounters_ReplaceTimedEncounters"),
        radar=tuple(int(slot) for slot, _ in radar_slots),
        daily=daily,
        dual_slot=slots("WildEncounters_ReplaceDualSlotEncounters"),
    )


def _check_time_of_day(repo_text: str, where: str) -> None:
    """Le matin garde les emplacements de base ; jour et crépuscule prennent `day`, nuit et fin de nuit `night`."""
    body = re.sub(r"\s+", " ", c_function(repo_text, "WildEncounters_ReplaceTimedEncounters", where))
    expected = (
        "if (timeOfDay == TIMEOFDAY_DAY || timeOfDay == TIMEOFDAY_TWILIGHT) { *timedSlot1 = "
        "encounterData->dayEncounters[0]; *timedSlot2 = encounterData->dayEncounters[1]; } else if (timeOfDay == "
        "TIMEOFDAY_NIGHT || timeOfDay == TIMEOFDAY_LATE_NIGHT) { *timedSlot1 = encounterData->nightEncounters[0]; "
        "*timedSlot2 = encounterData->nightEncounters[1]; }"
    )
    if expected not in body:
        raise ValueError(f"{where} : règle des moments de la journée inconnue")


def _tiles(repo: Gen4PretRepo) -> TileRules:
    path = repo.root / "src/map_tile_behavior.c"
    text = read_text(path)
    names = tile_names(repo)
    flags_path = repo.root / "include/constants/field/map_tile_behaviors.h"
    flag_values = {"TILE_BEHAVIOR_FLAG_NONE": 0, "TILE_BEHAVIOR_FLAG_SURFABLE": 1, "TILE_BEHAVIOR_FLAG_ENCOUNTER": 2}
    flag_values["TILE_BEHAVIOR_FLAG_SURFABLE_ENCOUNTER"] = 3
    if not all(f"#define {name}" in read_text(flags_path) for name in flag_values):
        raise ValueError(f"{flags_path} : drapeaux de comportement inconnus")
    entries = re.findall(r"\[(TILE_BEHAVIOR_\w+)\]\s*=\s*(\w+)", c_initializer(text, "sTileBehaviorFlags", path.name))
    flags = [0] * 256
    seen = set()
    for name, flag in entries:
        if (name not in names and name != "TILE_BEHAVIOR_MAX") or flag not in flag_values:
            raise ValueError(f"{path} : entrée de comportement inconnue : {name} = {flag}")
        if name in names:
            flags[names.index(name)] = flag_values[flag]
            seen.add(name)
    if len(seen) != 256:
        raise ValueError(f"{path} : {len(seen)} comportements décrits sur 256")

    def tested(function: str) -> frozenset[int]:
        body = c_function(text, function, path.name)
        found = re.findall(r"behavior == (TILE_BEHAVIOR_\w+)", body)
        if not found or re.sub(r"behavior == TILE_BEHAVIOR_\w+|\|\||return|[\s;]", "", body):
            raise ValueError(f"{path} : {function} illisible")
        return frozenset(names.index(name) for name in found)

    tall = tested("TileBehavior_IsTallGrass")
    grass = tall | tested("TileBehavior_IsVeryTallGrass") | tested("TileBehavior_IsMudWithGrass")
    if len(tall) != 1:
        raise ValueError(f"{path} : un seul comportement d'herbes hautes attendu")
    return TileRules(tuple(flags), next(iter(tall)), grass)


def _header_list(repo: Gen4PretRepo, file: str, table: str, headers: dict[str, int]) -> tuple[int, ...]:
    body = c_initializer(read_text(repo.root / file), table, file)
    names = re.findall(r"(?:\[\w+\]\s*=\s*)?(MAP_HEADER_\w+)", body)
    if not names or re.sub(r"(?:\[\w+\]\s*=\s*)?MAP_HEADER_\w+|[\s,]", "", body):
        raise ValueError(f"{file} : table {table} illisible")
    if unknown := [name for name in names if name not in headers]:
        raise ValueError(f"{file} : en-têtes inconnus dans {table} : {unknown}")
    return tuple(headers[name] for name in names)


def _single_header(repo: Gen4PretRepo, function: str, headers: dict[str, int]) -> int:
    body = c_function(read_text(repo.root / "src/map_header.c"), function, "map_header.c")
    match = re.fullmatch(r"\s*return mapHeaderID == (MAP_HEADER_\w+);\s*", body)
    if match is None or match.group(1) not in headers:
        raise ValueError(f"map_header.c : {function} illisible")
    return headers[match.group(1)]


def _great_marsh(repo: Gen4PretRepo, headers: dict[str, int]) -> tuple[int, ...]:
    where = "great_marsh_daily_encounters.c"
    text = read_text(repo.root / "src/overlay006" / where)
    body = c_function(text, "GreatMarsh_GetAreaNumFromMapId", where)
    cases = re.findall(r"case (MAP_HEADER_\w+):\s*areaNum = (\d+);\s*break;", body)
    if [int(number) for _, number in cases] != list(range(6)) or any(name not in headers for name, _ in cases):
        raise ValueError(f"{where} : zones du Grand Marais illisibles")
    replace = re.sub(r"\s+", " ", c_function(text, "ReplaceGreatMarshDailyEncounters", where))
    if "if (nationalDexObtained) { encDataGroup = 9; } else { encDataGroup = 10; }" not in replace:
        raise ValueError(f"{where} : listes quotidiennes du Grand Marais inconnues")
    if "u8 encounterIndex = ((dailyMon >> (5 * areaNum)) & 0x1f);" not in replace:
        raise ValueError(f"{where} : tirage quotidien du Grand Marais inconnu")
    return tuple(headers[name] for name, _ in cases)


def _feebas_levels(repo: Gen4PretRepo) -> tuple[int, int]:
    body = c_function(read_text(repo.root / "src/overlay006/feebas_fishing.c"), "LoadFeebasLevelRange", "feebas")
    match = re.fullmatch(r"\s*\(\*maxLevel\) = (\d+);\s*\(\*minLevel\) = (\d+);\s*", body)
    if match is None:
        raise ValueError("feebas_fishing.c : niveaux de Barpau illisibles")
    return int(match.group(2)), int(match.group(1))


def _roamer_headers(repo: Gen4PretRepo, headers: dict[str, int]) -> tuple[int, ...]:
    return _header_list(repo, "src/roaming_pokemon.c", "RoamingPokemonRoutes", headers)


def _roamers(repo: Gen4PretRepo) -> tuple[tuple[int, int], ...]:
    text = read_text(repo.root / "src/roaming_pokemon.c")
    body = c_function(text, "RoamingPokemon_ActivateSlot", "roaming_pokemon.c")
    cases = re.findall(r"case (ROAMING_SLOT_\w+):\s*species = SPECIES_(\w+);\s*level = (\d+);\s*break;", body)
    species = metang_enum(repo.root / "generated/species.txt")
    scripts = repo.root / "res/field/scripts"
    activated = {
        slot
        for path in sorted(scripts.glob("*.s"))
        for slot in re.findall(r"ActivateRoamingPokemon (ROAMING_SLOT_\w+)", read_text(path))
    }
    if not cases or not activated <= {slot for slot, _, _ in cases}:
        raise ValueError(f"roaming_pokemon.c : errants illisibles ou inconnus : {sorted(activated)}")
    return tuple((species[f"SPECIES_{name}"], int(level)) for slot, name, level in cases if slot in activated)


def _unown_forms(repo: Gen4PretRepo, wild: str, where: str) -> tuple[tuple[int, ...], ...]:
    """Groupes de formes de Zarbi (WildEncounters_UnownTables) ; les formes de Sancoki et Tritosor suivent les champs
    rate_form0 et rate_form1 (Est si non nul), comme le vérifie la lecture de AddWildMonToParty."""
    forms = {name: value for name, value in _unown_constants(repo).items()}
    arrays = {
        name: tuple(forms[value] for value in re.findall(r"UNOWN_FORM_\w+", body))
        for name, body in re.findall(r"static const u8 (Unown\w+)\[\] = \{(.*?)\};", wild, re.DOTALL)
    }
    table = re.findall(
        r"\{\s*(0x[0-9A-Fa-f]+|\d+),\s*(Unown\w+)\s*\}", c_initializer(wild, "WildEncounters_UnownTables", where)
    )
    if not table or any(int(count, 0) != len(arrays.get(name, ())) for count, name in table):
        raise ValueError(f"{where} : groupes de formes de Zarbi illisibles")
    party = re.sub(r"\s+", " ", c_function(wild, "AddWildMonToParty", where))
    shape = (
        "if (species == SPECIES_SHELLOS) { setForm = TRUE; if (!encounterFieldParams->encounterRatesForms[0]) "
        "{ form = 0; } else { form = 1; } } else if (species == SPECIES_GASTRODON) { setForm = TRUE; if "
        "(!encounterFieldParams->encounterRatesForms[1]) { form = 0; } else { form = 1; } }"
    )
    if shape not in party:
        raise ValueError(f"{where} : formes de Sancoki et Tritosor inconnues")
    return tuple(arrays[name] for _, name in table)


def _unown_constants(repo: Gen4PretRepo) -> dict[str, int]:
    path = repo.root / "include/constants/forms.h"
    values = {name: int(value, 0) for name, value in re.findall(r"#define (UNOWN_FORM_\w+)\s+(\d+)", read_text(path))}
    if len(values) < 28:
        raise ValueError(f"{path} : formes de Zarbi incomplètes")
    return values


def _honey(repo: Gen4PretRepo, headers: dict[str, int]) -> HoneyRules:
    where = "honey_tree.c"
    text = read_text(repo.root / "src/overlay005" / where)
    tables = c_initializer(text, "sEncounterTableIndexes_DPt", where)
    indexes = tuple(int(value, 0) for value in re.findall(r"0x[0-9A-Fa-f]+|\d+", tables))
    group_body = re.sub(r"\s+", " ", c_function(text, "GetTreeEncounterGroup", where))
    if group_body.count("} } else {") != 1 or "if (isMunchlaxTree) {" not in group_body:
        raise ValueError(f"{where} : groupes des arbres à Miel illisibles")
    munchlax, normal = group_body.split("if (isMunchlaxTree) {", 1)[1].split("} } else {")
    wild = read_text(repo.root / "src/overlay006/wild_encounters.c")
    level_body = c_function(wild, "CreateWildMon_HoneyTree", "wild_encounters.c")
    level = re.search(r"u8 levelVariance = (\d+) - (\d+) \+ 1;", level_body)
    if len(indexes) != 3 or level is None:
        raise ValueError(f"{where} : arbres à Miel illisibles")
    return HoneyRules(
        headers=_header_list(repo, f"src/overlay005/{where}", "sHoneyTreeMapHeaderIDs", headers),
        tables=(("platinum", (indexes[0], indexes[1], indexes[2])),),
        slot_rates=_value_rates(c_function(text, "GetTreeEncounterSlot", where), "slot", HONEY_SLOTS, where),
        levels=(int(level.group(2)), int(level.group(1))),
        normal_groups=_group_rates(normal, where),
        munchlax_groups=_group_rates(munchlax, where),
        model=repo.names.order("res/field/props/models/map_prop_models.order")["honey_tree.nsbmd"],
    )


def _value_rates(body: str, target: str, count: int, where: str) -> tuple[int, ...]:
    """Probabilité de chaque valeur affectée à `*target` par une suite `if (roll < N) … else …`."""
    pairs = re.findall(rf"roll < (\d+)\)\s*\{{\s*\*{target} = (\w+);", body)
    final = re.findall(rf"\}} else \{{\s*\*{target} = (\w+);\s*\}}\s*$", body.strip())
    if not pairs or len(final) != 1:
        raise ValueError(f"{where} : tirage de {target} illisible")
    return _distribution([(int(bound), value) for bound, value in pairs], final[0], count, where)


def _group_rates(body: str, where: str) -> tuple[int, int, int, int]:
    groups = {"TREE_GROUP_NO_ENCOUNTER": "0", "TREE_GROUP_A": "1", "TREE_GROUP_B": "2", "TREE_GROUP_C": "3"}
    pairs = re.findall(r"roll < (\d+)\)\s*\{\s*\*group = (TREE_GROUP_\w+);", body)
    final = re.findall(r"\}\s*else\s*\{\s*\*group = (TREE_GROUP_\w+);", body)
    if not pairs or not final:
        raise ValueError(f"{where} : groupes des arbres à Miel illisibles")
    rates = _distribution([(int(bound), groups[name]) for bound, name in pairs], groups[final[-1]], 4, where)
    return rates[0], rates[1], rates[2], rates[3]


def _distribution(pairs: list[tuple[int, str]], final: str, count: int, where: str) -> tuple[int, ...]:
    rates = [0] * count
    low = 0
    for bound, value in [*pairs, (100, final)]:
        index = int(value, 0)
        if not 0 <= index < count or bound <= low:
            raise ValueError(f"{where} : tirage incohérent : {pairs} puis {final}")
        rates[index] += bound - low
        low = bound
    return tuple(rates)
