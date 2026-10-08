"""Rencontres aléatoires de la 2e génération, lues dans pret comme le moteur les tire, version par version.

- herbes et grottes (data/wild/*_grass.asm) : 7 emplacements par moment de la journée (GrassMonProbTable) ;
- surf (data/wild/*_water.asm) : 3 emplacements (WaterMonProbTable) ;
- essaims (data/wild/swarm_*.asm) : la table de la carte pendant un essaim (condition swarm-yes) ;
- pêche (data/wild/fish.asm) : groupe de pêche de l'en-tête de la carte, une table par canne ; un emplacement
  « time_group » change d'espèce la nuit (Fish, .TimeEncounter), et les essaims de Qwilfish et de Remoraid
  remplacent le groupe de leur carte (GetFishGroupIndex). Seules les cartes qui ont de l'eau ont une pêche ;
- Coup d'Boule (data/wild/treemons.asm) : table commune des arbres ordinaires, table rare des autres (GetTreeMon) ;
- Éclate-Roc (RockMonMaps) et Concours de capture d'insectes (data/wild/bug_contest_mons.asm).

Une carte de TreeMonMaps sans arbre à Coup d'Boule (Routes 45 et 46), ou de RockMonMaps sans rocher (Puits
Ramoloss), n'a pas ces rencontres : le moteur ne peut pas les déclencher.

Méthodes et conditions portent les identifiants PokéAPI. Une table identique aux trois moments de la journée n'a
pas de condition. Les probabilités sont les pourcentages écrits dans pret : « 70 percent + 1 » vaut 70 % (le
« + 1 » compense l'arrondi de n * 255 / 100 du seuil).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .pret_source import conditional_lines, macro_args, parse_int, source_lines

if TYPE_CHECKING:
    from .pret_gen2 import Gen2PretRepo
    from .pret_models import PretMap

Cell = tuple[int, int]

TIMES = ("time-morning", "time-day", "time-night")
SWARM = "swarm-yes"
BUG_CONTEST = "bug-catching-contest-yes"
# Méthodes PokéAPI des rencontres lues ici : celles de PokéAPI pour ces méthodes sont écartées.
WILD_METHODS = frozenset(
    {"walk", "surf", "old-rod", "good-rod", "super-rod", "headbutt", "headbutt-high", "rock-smash"}
)
_RODS = ("old-rod", "good-rod", "super-rod")
# GetFishGroupIndex : pendant un essaim, ces groupes laissent place à celui de l'essaim.
_FISH_SWARMS = {"FISHGROUP_QWILFISH": "FISHGROUP_QWILFISH_SWARM", "FISHGROUP_REMORAID": "FISHGROUP_REMORAID_SWARM"}
_NO_FISH = "FISHGROUP_NONE"
# GetTreeMons ignore l'ensemble 0 et les deux derniers : aucun Pokémon ne tombe de ces arbres.
_IGNORED_TREE_SETS = frozenset({"TREEMON_SET_NONE", "TREEMON_SET_UNUSED", "TREEMON_SET_CITY"})
# Carte où se déroule le Concours (le script d'inscription y envoie le joueur).
CONTEST_MAP = "NATIONAL_PARK_BUG_CONTEST"
_WATER_PERMISSION = "WATER_TILE"
_SMASH_ROCK = "jumpstd SmashRockScript"
_SPECIAL_BATTLE_TYPES = frozenset({"BATTLETYPE_FORCEITEM", "BATTLETYPE_FORCESHINY"})


@dataclass(frozen=True)
class WildSlot:
    species: str  # constante pret (ex. RATTATA)
    min_level: int
    max_level: int
    chance: int  # en %


@dataclass(frozen=True)
class WildTable:
    map_const: str
    method: str  # méthode de rencontre PokéAPI
    conditions: tuple[str, ...]  # valeurs de conditions PokéAPI, triées
    slots: tuple[WildSlot, ...]


@dataclass(frozen=True)
class SpecialBattle:
    """Combat sauvage scripté dont le type change le Pokémon : objet tenu forcé ou chromatique (BATTLETYPE_…)."""

    map_const: str
    species: str
    battle_type: str


def wild_tables(repo: Gen2PretRepo, symbol: str) -> list[WildTable]:
    """Toutes les tables de rencontres aléatoires du jeu dans la version `symbol` (ex. _GOLD)."""
    defined = frozenset({symbol})
    tables = _land_and_water(repo, defined)
    tables += _fishing(repo, defined)
    tables += _trees_and_rocks(repo, defined)
    tables.append(_bug_contest(repo, defined))
    return tables


def headbutt_maps(repo: Gen2PretRepo) -> frozenset[str]:
    """Cartes où Coup d'Boule fait tomber des Pokémon des arbres (TreeMonMaps, hors ensembles ignorés)."""
    maps = _tree_maps(repo, "TreeMonMaps:")
    return frozenset(const for const, tree_set in maps if tree_set not in _IGNORED_TREE_SETS)


def rock_smash_maps(repo: Gen2PretRepo) -> frozenset[str]:
    """Cartes où Éclate-Roc fait surgir des Pokémon des rochers (RockMonMaps)."""
    return frozenset(const for const, _ in _tree_maps(repo, "RockMonMaps:"))


def roaming_maps(repo: Gen2PretRepo) -> list[str]:
    """Cartes que parcourent les Pokémon errants (RoamMaps : la première carte de chaque ligne)."""
    lines = source_lines(repo.path("data/wild/roammon_maps.asm"))
    result = [macro_args(line, "roam_map")[0] for line in lines if line.startswith("roam_map ")]
    if not result:
        raise ValueError(f"{repo.root.name} : aucune carte dans data/wild/roammon_maps.asm")
    return result


def special_battles(repo: Gen2PretRepo) -> list[SpecialBattle]:
    """Combats sauvages scriptés à objet forcé ou chromatiques : loadwildmon et loadvar VAR_BATTLETYPE dans un même
    bloc de script, avant startbattle."""
    result: list[SpecialBattle] = []
    for const, header in sorted(repo.headers.items()):
        script_file = repo.script_files.get(header.label)
        if script_file is None:
            continue
        for block in script_file.blocks.values():
            species, battle_type = None, None
            for line in block.lines:
                if line.startswith("loadwildmon "):
                    species = macro_args(line, "loadwildmon")[0]
                elif line.startswith("loadvar VAR_BATTLETYPE,"):
                    battle_type = macro_args(line, "loadvar")[1]
                elif line == "startbattle" and species and battle_type in _SPECIAL_BATTLE_TYPES:
                    battle = SpecialBattle(const, species, battle_type)
                    if battle not in result:
                        result.append(battle)
    return result


def smash_rocks(repo: Gen2PretRepo, pret_map: PretMap) -> list[Cell]:
    """Rochers qu'Éclate-Roc brise (objets dont le script est SmashRockScript), en pas de 16 px."""
    script_file = repo.script_files[repo.headers[pret_map.const].label]
    return [
        (obj.x, obj.y)
        for obj in pret_map.objects
        if obj.text and script_file.has_label(obj.text) and script_file.blocks[obj.text].lines == (_SMASH_ROCK,)
    ]


def has_water(repo: Gen2PretRepo, pret_map: PretMap) -> bool:
    """Vrai si une case de la carte est de l'eau, où l'on peut pêcher."""
    permissions = repo.collisions.permissions
    return any(permissions[collision] == _WATER_PERMISSION for collision in _collisions(repo, pret_map))


def has_headbutt_trees(repo: Gen2PretRepo, pret_map: PretMap) -> bool:
    """Vrai si la carte a un arbre où Coup d'Boule peut faire tomber un Pokémon (CheckHeadbuttTreeTile)."""
    return not repo.collisions.headbutt_trees.isdisjoint(_collisions(repo, pret_map))


def _collisions(repo: Gen2PretRepo, pret_map: PretMap) -> set[int]:
    """Collisions des cases de la carte."""
    tileset = repo.tilesets[pret_map.tileset]
    return {collision for block in set(pret_map.blocks) for collision in tileset.collisions[block]}


# --- Herbes, grottes et surf ------------------------------------------------------------------


def _land_and_water(repo: Gen2PretRepo, defined: frozenset[str]) -> list[WildTable]:
    grass = _probabilities(repo, "GrassMonProbTable:")
    water = _probabilities(repo, "WaterMonProbTable:")
    tables: list[WildTable] = []
    for name, extra in (("johto", ()), ("kanto", ()), ("swarm", (SWARM,))):
        for const, slots in _wildmons(repo, f"data/wild/{name}_grass.asm", "grass", defined).items():
            periods = _split(slots, len(grass), len(TIMES), const)
            tables += _timed(const, "walk", extra, [_chances(period, grass) for period in periods])
        for const, slots in _wildmons(repo, f"data/wild/{name}_water.asm", "water", defined).items():
            tables.append(_table(const, "surf", extra, _chances(_split(slots, len(water), 1, const)[0], water)))
    return tables


def _probabilities(repo: Gen2PretRepo, label: str) -> list[int]:
    """Part de chaque emplacement (en %), d'après les seuils cumulés « mon_prob » d'une table."""
    lines = source_lines(repo.path("data/wild/probabilities.asm"))
    thresholds = []
    for line in lines[lines.index(label) + 1 :]:
        if line.endswith(":"):
            break
        if line.startswith("mon_prob "):
            thresholds.append(parse_int(macro_args(line, "mon_prob")[0]))
    return _differences(thresholds, label)


def _wildmons(repo: Gen2PretRepo, relative: str, kind: str, defined: frozenset[str]) -> dict[str, list[WildSlot]]:
    """Carte -> emplacements (niveau, espèce) de ses tables def_<kind>_wildmons, sans les taux de rencontre."""
    result: dict[str, list[WildSlot]] = {}
    current: str | None = None
    for line in conditional_lines(repo.path(relative), defined):
        if line.startswith(f"def_{kind}_wildmons "):
            current = line.split()[1]
            if current in result:
                raise ValueError(f"{relative} : {current} a deux tables")
            result[current] = []
        elif line == f"end_{kind}_wildmons":
            current = None
        elif current and line.startswith("db ") and "percent" not in line:
            level, species = macro_args(line, "db")
            result[current].append(WildSlot(species, int(level), int(level), 0))
    return result


def _split(slots: list[WildSlot], size: int, count: int, const: str) -> list[list[WildSlot]]:
    if len(slots) != size * count:
        raise ValueError(f"{const} : {len(slots)} emplacements au lieu de {size * count}")
    return [slots[index * size : (index + 1) * size] for index in range(count)]


def _chances(slots: list[WildSlot], chances: list[int]) -> tuple[WildSlot, ...]:
    return tuple(WildSlot(s.species, s.min_level, s.max_level, c) for s, c in zip(slots, chances, strict=True))


def _timed(const: str, method: str, extra: tuple[str, ...], periods: list[tuple[WildSlot, ...]]) -> list[WildTable]:
    """Une table par moment de la journée (matin, jour, nuit), ou une seule si elles sont identiques."""
    if all(period == periods[0] for period in periods):
        return [_table(const, method, extra, periods[0])]
    return [_table(const, method, (*extra, time), period) for time, period in zip(TIMES, periods, strict=True)]


def _table(const: str, method: str, conditions: tuple[str, ...], slots: tuple[WildSlot, ...]) -> WildTable:
    if sum(slot.chance for slot in slots) != 100:
        raise ValueError(f"{const} ({method}) : probabilités différentes de 100 % : {slots}")
    return WildTable(const, method, tuple(sorted(conditions)), slots)


def _differences(thresholds: list[int], where: str) -> list[int]:
    """Parts successives de seuils cumulés (30, 60, 80… -> 30, 30, 20…), qui doivent finir à 100."""
    if not thresholds or thresholds[-1] != 100:
        raise ValueError(f"{where} : seuils cumulés invalides {thresholds}")
    return [high - low for low, high in zip([0, *thresholds], thresholds, strict=False)]


# --- Pêche -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class _FishSlot:
    threshold: int  # seuil cumulé en %
    species: str | None  # None : emplacement time_group
    value: int  # niveau, ou numéro de la ligne de TimeFishGroups


def _fishing(repo: Gen2PretRepo, defined: frozenset[str]) -> list[WildTable]:
    lines = conditional_lines(repo.path("data/wild/fish.asm"), defined)
    groups = _fish_groups(repo, lines)
    labels = _fish_labels(lines)
    by_time = _time_fish_groups(lines)
    tables: list[WildTable] = []
    for const, header in sorted(repo.headers.items()):
        if header.fishing_group == _NO_FISH or not has_water(repo, repo.maps[const]):
            continue
        variants = [(header.fishing_group, ())]
        if header.fishing_group in _FISH_SWARMS:
            variants.append((_FISH_SWARMS[header.fishing_group], (SWARM,)))
        for group, extra in variants:
            for rod, label in zip(_RODS, groups[group], strict=True):
                slots = labels[label]
                periods = [_fish_period(slots, by_time, night) for night in (False, False, True)]
                tables += _timed(const, rod, extra, periods)
    return tables


def _fish_groups(repo: Gen2PretRepo, lines: list[str]) -> dict[str, tuple[str, str, str]]:
    """Groupe de pêche (FISHGROUP_…) -> labels de ses tables (canne, Super Canne, Méga Canne)."""
    consts = [
        const
        for const in repo.consts("constants/map_data_constants.asm")
        if const.startswith("FISHGROUP_") and const != _NO_FISH
    ]
    entries = [macro_args(line, "fishgroup")[1:] for line in lines if line.startswith("fishgroup ")]
    if len(entries) != len(consts):
        raise ValueError(f"{repo.root.name} : {len(entries)} groupes de pêche pour {len(consts)} constantes")
    return {const: (old, good, super_) for const, (old, good, super_) in zip(consts, entries, strict=True)}


def _fish_labels(lines: list[str]) -> dict[str, list[_FishSlot]]:
    """Label local (.Shore_Old…) -> emplacements ; plusieurs labels peuvent précéder la même table."""
    result: dict[str, list[_FishSlot]] = {}
    pending: list[str] = []
    current: list[_FishSlot] | None = None
    for line in lines:
        if line.startswith(".") and line.endswith(":"):
            if current is not None:
                pending, current = [], None
            pending.append(line[:-1])
        elif line.startswith("db ") and pending:
            if current is None:
                current = []
                result |= dict.fromkeys(pending, current)
            current.append(_fish_slot(macro_args(line, "db")))
        else:
            pending, current = [], None
    return result


def _fish_slot(args: list[str]) -> _FishSlot:
    threshold = int(args[0].split()[0])
    if args[1].startswith("time_group "):
        return _FishSlot(threshold, None, int(args[1].split()[1]))
    return _FishSlot(threshold, args[1], int(args[2]))


def _time_fish_groups(lines: list[str]) -> list[tuple[WildSlot, WildSlot]]:
    """Lignes de TimeFishGroups : (espèce et niveau de jour, de nuit)."""
    start = lines.index("TimeFishGroups:") + 1
    result = []
    for line in lines[start:]:
        if not line.startswith("db "):
            break
        day, day_level, night, night_level = (macro_args(line, "db")[index] for index in range(4))
        result.append((_fixed(day, int(day_level)), _fixed(night, int(night_level))))
    return result


def _fish_period(slots: list[_FishSlot], by_time: list[tuple[WildSlot, WildSlot]], night: bool) -> tuple[WildSlot, ...]:
    chances = _differences([slot.threshold for slot in slots], "fish.asm")
    result = []
    for slot, chance in zip(slots, chances, strict=True):
        base = by_time[slot.value][1 if night else 0] if slot.species is None else _fixed(slot.species, slot.value)
        result.append(WildSlot(base.species, base.min_level, base.max_level, chance))
    return tuple(result)


def _fixed(species: str, level: int) -> WildSlot:
    return WildSlot(species, level, level, 0)


# --- Coup d'Boule, Éclate-Roc et Concours -------------------------------------------------------


def _trees_and_rocks(repo: Gen2PretRepo, defined: frozenset[str]) -> list[WildTable]:
    lines = conditional_lines(repo.path("data/wild/treemons.asm"), defined)
    sets = _tree_sets(repo, lines)
    tables: list[WildTable] = []
    for const, tree_set in _tree_maps(repo, "TreeMonMaps:"):
        if tree_set in _IGNORED_TREE_SETS or not has_headbutt_trees(repo, repo.maps[const]):
            continue
        common, rare = sets[tree_set]
        tables.append(_table(const, "headbutt", (), common))
        tables.append(_table(const, "headbutt-high", (), rare))
    for const, rock_set in _tree_maps(repo, "RockMonMaps:"):
        if smash_rocks(repo, repo.maps[const]):
            tables.append(_table(const, "rock-smash", (), sets[rock_set][0]))
    return tables


def _tree_maps(repo: Gen2PretRepo, label: str) -> list[tuple[str, str]]:
    """(carte, ensemble TREEMON_SET_…) d'une table de data/wild/treemon_maps.asm, jusqu'à « db -1 »."""
    lines = source_lines(repo.path("data/wild/treemon_maps.asm"))
    result = []
    for line in lines[lines.index(label) + 1 :]:
        if not line.startswith("treemon_map "):
            break
        const, tree_set = macro_args(line, "treemon_map")
        result.append((const, tree_set))
    return result


def _tree_sets(repo: Gen2PretRepo, lines: list[str]) -> dict[str, list[tuple[WildSlot, ...]]]:
    """Ensemble TREEMON_SET_… -> ses tables (commune puis rare ; une seule pour les rochers)."""
    consts = [
        const for const in repo.consts("constants/pokemon_data_constants.asm") if const.startswith("TREEMON_SET_")
    ]
    pointers = [macro_args(line, "dw")[0] for line in lines if line.startswith("dw ")]
    if len(pointers) != len(consts):
        raise ValueError(f"{repo.root.name} : {len(pointers)} tables d'arbres pour {len(consts)} ensembles")
    tables: dict[str, list[tuple[WildSlot, ...]]] = {}
    pending: list[str] = []
    current: list[WildSlot] = []
    in_data = False
    for line in lines:
        if line.endswith(":"):
            if in_data:
                pending, in_data = [], False
            pending.append(line[:-1])
        elif line.startswith("db ") and pending:
            in_data = True
            if line == "db -1":
                for label in pending:
                    tables.setdefault(label, []).append(tuple(current))
                current = []
            else:
                chance, species, level = macro_args(line, "db")
                current.append(WildSlot(species, int(level), int(level), int(chance)))
        else:
            pending = []
    return {const: tables.get(label, []) for const, label in zip(consts, pointers, strict=True)}


def _bug_contest(repo: Gen2PretRepo, defined: frozenset[str]) -> WildTable:
    """Pokémon du Concours (ContestMons, tirés jusqu'à « -1 » par ChooseWildEncounter_BugContest)."""
    slots = []
    for line in conditional_lines(repo.path("data/wild/bug_contest_mons.asm"), defined):
        if not line.startswith("db "):
            continue
        args = macro_args(line, "db")
        if args[0] == "-1":
            break
        chance, species, low, high = args
        slots.append(WildSlot(species, int(low), int(high), int(chance)))
    return _table(CONTEST_MAP, "walk", (BUG_CONTEST,), tuple(slots))
