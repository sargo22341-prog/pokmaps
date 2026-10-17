"""Dresseurs DS : équipes, objets tenus, attaques et combats doubles, lus dans chaque dépôt.

Platine décrit chaque dresseur dans res/trainers/data/<nom>.json, numéroté par generated/trainers.txt ; la forme
des données de l'équipe (attaques, objets) est choisie, comme le fait tools/dataproc/src/trainerproc.c, d'après
le premier Pokémon. Diamant/Perle les liste dans files/poketool/trainer/trdata.json, avec cette forme explicite.

Sans attaques écrites, le moteur donne à chaque Pokémon ses attaques par défaut (BoxPokemon_SetDefaultMoves de
Platine, InitBoxMonMoveset de Diamant/Perle) : les quatre dernières attaques apprises jusqu'à son niveau, sans
doublon. Il les calcule à la création du Pokémon, avant de lui donner sa forme (TrainerData_BuildParty,
CreateNPCTrainerParty) : la liste d'attaques est donc toujours celle de la forme de base.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .pret_gen3_trainers import default_moves
from .pret_gen4_source import metang_enum, read_json
from .pret_items_gen4 import ds_item_constants

MAX_PARTY = 6
MAX_TRAINER_ITEMS = 4
MAX_IV_SCALE = 255
# Le champ ivScale est un u16 (TrainerMonBase, union TrainerMon) ; les sources dépassent parfois MAX_IV_SCALE.
_MAX_IV_FIELD = 0xFFFF
_INIT_IVS_RANDOM = 32
_MOVE_SLOTS = 4
_PLATINUM_KEYS = frozenset({"name", "class", "items", "ai_flags", "double_battle", "party", "messages"})
_PLATINUM_MON_KEYS = frozenset({"species", "form", "level", "item", "moves", "iv_scale", "ball_seal"})
_DP_KEYS = frozenset({"index", "type", "class", "name", "unk2", "items", "unkC", "doubleBattle", "party"})
# Forme des données d'équipe de Diamant/Perle (TRTYPE_*) : attaques écrites, objet tenu.
_DP_TYPES = {
    "TRTYPE_MON": (False, False),
    "TRTYPE_MON_MOVES": (True, False),
    "TRTYPE_MON_ITEM": (False, True),
    "TRTYPE_MON_ITEM_MOVES": (True, True),
}
# Valeur du champ doubleBattle de Diamant/Perle pour un combat double (BATTLE_TYPE_DOUBLES).
_DP_DOUBLE = 2
_DP_NAME_PREFIX = "{TRNAME}"

Learnsets = dict[str, tuple[tuple[int, str], ...]]


@dataclass(frozen=True)
class Gen4TrainerPokemon:
    species: str
    form: int
    level: int
    move_slots: tuple[str, ...]
    item: str | None
    iv_scale: int
    custom_moves: bool

    @property
    def moves(self) -> tuple[str, ...]:
        return tuple(move for move in self.move_slots if move != "MOVE_NONE")

    @property
    def fixed_iv(self) -> int | None:
        """IV de chaque statistique : ivScale * MAX_IVS_SINGLE_STAT / MAX_IV_SCALE, rangé dans un octet. Au-delà de
        31 (INIT_IVS_RANDOM), le moteur tire les IV au hasard : c'est le cas de l'Élekable de Tanguy en Platine,
        dont l'échelle vaut 2500 au lieu de 250 au plus."""
        ivs = self.iv_scale * 31 // MAX_IV_SCALE & 0xFF
        return ivs if ivs < _INIT_IVS_RANDOM else None


@dataclass(frozen=True)
class Gen4Trainer:
    id: int
    const: str | None  # constante de Platine ; Diamant/Perle ne nomme ses dresseurs que par leur numéro
    trainer_class: str
    name: str
    double_battle: bool
    items: tuple[str, ...]
    party: tuple[Gen4TrainerPokemon, ...]


@dataclass(frozen=True)
class _Known:
    learnsets: Learnsets
    moves: frozenset[str]
    items: frozenset[str]
    classes: frozenset[str]


def read_trainers(root: Path, repo: str) -> dict[int, Gen4Trainer]:
    """Dresseurs par numéro (celui des scripts et des événements), sans TRAINER_NONE."""
    if repo == "pokeplatinum":
        trainers = _platinum(root, _known(root, repo))
    elif repo == "pokediamond":
        trainers = _diamond_pearl(root, _known(root, repo))
    else:
        raise ValueError(f"Dépôt de dresseurs DS inconnu : {repo}")
    if not trainers or 0 in trainers:
        raise ValueError(f"{root} : dresseurs absents ou numéro 0 utilisé")
    return trainers


def _known(root: Path, repo: str) -> _Known:
    items = frozenset({*ds_item_constants(root, repo), "ITEM_NONE"})
    if repo == "pokeplatinum":
        moves = frozenset(metang_enum(root / "generated/moves.txt"))
        classes = frozenset(metang_enum(root / "generated/trainer_classes.txt"))
        return _Known(_platinum_learnsets(root), moves, items, classes)
    data = read_json(root / "files/poketool/waza/waza_tbl.json")["waza_tbl"]
    text = (root / "include/constants/trainer_classes.h").read_text(encoding="utf-8")
    classes = frozenset(re.findall(r"#define\s+(TRAINER_CLASS_\w+)\s", text))
    return _Known(_dp_learnsets(root), frozenset(row["name"] for row in data), items, classes)


def _platinum_learnsets(root: Path) -> Learnsets:
    result = {}
    for path in sorted((root / "res/pokemon").glob("*/data.json")):
        rows = read_json(path)["learnset"]["by_level"]
        result[f"SPECIES_{path.parent.name.upper()}"] = tuple((int(level), str(move)) for level, move in rows)
    return result


def _dp_learnsets(root: Path) -> Learnsets:
    rows = read_json(root / "files/poketool/personal/wotbl.json")["wotbl"]
    return {
        f"SPECIES_{row['species']}": tuple((int(m["level"]), f"MOVE_{m['move']}") for m in row["moves"])
        for row in rows
        if row["species"] != "NONE"
    }


def _platinum(root: Path, known: _Known) -> dict[int, Gen4Trainer]:
    numbers = metang_enum(root / "generated/trainers.txt")
    result = {}
    for path in sorted((root / "res/trainers/data").glob("*.json")):
        const = f"TRAINER_{path.stem.upper()}"
        if const not in numbers:
            raise ValueError(f"{path} : dresseur absent de generated/trainers.txt")
        if numbers[const] == 0:
            continue
        data = read_json(path)
        if set(data) != _PLATINUM_KEYS:
            raise ValueError(f"{path} : champs de dresseur inattendus : {sorted(set(data) ^ _PLATINUM_KEYS)}")
        party = data["party"]
        # trainerproc.c : la forme de l'équipe se lit sur le premier Pokémon.
        if not party:
            raise ValueError(f"{path} : équipe vide")
        moves, items = isinstance(party[0]["moves"], list), party[0]["item"] is not None
        mons = tuple(_platinum_mon(mon, moves, items, known, str(path)) for mon in party)
        result[numbers[const]] = _trainer(
            numbers[const], const, data["class"], data["name"], data["double_battle"], data["items"], mons, known
        )
    return result


def _platinum_mon(mon: dict, moves: bool, items: bool, known: _Known, where: str) -> Gen4TrainerPokemon:
    if set(mon) != _PLATINUM_MON_KEYS:
        raise ValueError(f"{where} : champs de Pokémon inattendus : {sorted(set(mon) ^ _PLATINUM_MON_KEYS)}")
    if isinstance(mon["moves"], list) != moves or (mon["item"] is not None) != items:
        raise ValueError(f"{where} : attaques ou objets écrits pour une partie de l'équipe seulement")
    return _pokemon(mon["species"], mon["form"], mon["level"], mon["moves"], mon["item"], mon["iv_scale"], known, where)


def _diamond_pearl(root: Path, known: _Known) -> dict[int, Gen4Trainer]:
    result = {}
    for row in read_json(root / "files/poketool/trainer/trdata.json")["trdata"]:
        where = f"{root} trdata {row.get('index')}"
        if set(row) != _DP_KEYS or row["type"] not in _DP_TYPES or row["doubleBattle"] not in {0, _DP_DOUBLE}:
            raise ValueError(f"{where} : dresseur illisible")
        if row["index"] == 0:
            continue
        moves, items = _DP_TYPES[row["type"]]
        mons = []
        for mon in row["party"]:
            if ("moves" in mon, "item" in mon) != (moves, items):
                raise ValueError(f"{where} : Pokémon de forme différente de {row['type']}")
            level, scale = mon["level"], mon["difficulty"]
            mons.append(_pokemon(mon["species"], 0, level, mon.get("moves"), mon.get("item"), scale, known, where))
        name = row["name"].removeprefix(_DP_NAME_PREFIX)
        result[row["index"]] = _trainer(
            row["index"], None, row["class"], name, row["doubleBattle"] == _DP_DOUBLE, row["items"], tuple(mons), known
        )
    if sorted(result) != list(range(1, len(result) + 1)):
        raise ValueError(f"{root} : numéros de dresseurs non consécutifs")
    return result


def _pokemon(
    species: str, form: int, level: int, moves: list | None, item: str | None, iv_scale: int, known: _Known, where: str
) -> Gen4TrainerPokemon:
    if species not in known.learnsets or not 1 <= level <= 100 or not 0 <= iv_scale <= _MAX_IV_FIELD or form < 0:
        raise ValueError(f"{where} : Pokémon de dresseur invalide : {species} niveau {level}")
    if moves is None:
        slots = default_moves(known.learnsets[species], level)
    elif 1 <= len(moves) <= _MOVE_SLOTS:
        slots = tuple(moves)
    else:
        raise ValueError(f"{where} : {species} : une à quatre attaques attendues")
    slots += ("MOVE_NONE",) * (_MOVE_SLOTS - len(slots))
    if set(slots) - known.moves or all(move == "MOVE_NONE" for move in slots):
        raise ValueError(f"{where} : {species} : attaques inconnues ou absentes : {slots}")
    if item is not None and item not in known.items:
        raise ValueError(f"{where} : {species} : objet tenu inconnu : {item}")
    held = None if item in {None, "ITEM_NONE"} else item
    return Gen4TrainerPokemon(species, form, level, slots, held, iv_scale, moves is not None)


def _trainer(
    number: int,
    const: str | None,
    trainer_class: str,
    name: str,
    double: object,
    items: list,
    party: tuple[Gen4TrainerPokemon, ...],
    known: _Known,
) -> Gen4Trainer:
    where = const or f"dresseur {number}"
    if trainer_class not in known.classes or type(double) is not bool or not 1 <= len(party) <= MAX_PARTY:
        raise ValueError(f"{where} : classe, type de combat ou taille d'équipe invalide")
    if len(items) > MAX_TRAINER_ITEMS or set(items) - known.items:
        raise ValueError(f"{where} : objets de combat invalides : {items}")
    kept = tuple(item for item in items if item != "ITEM_NONE")
    return Gen4Trainer(number, const, trainer_class, name, double, kept, party)
