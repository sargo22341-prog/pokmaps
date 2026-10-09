"""Tables sauvages GBA : probabilités des emplacements et sélection de la version."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from .pret_gen2_wild import WildSlot
from .pret_gen3_source import read_json

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo

REPLACED_METHODS = frozenset({"walk", "surf", "seaweed", "rock-smash", "old-rod", "good-rod", "super-rod"})
_RATES = {
    "land_mons": (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1),
    "water_mons": (60, 30, 5, 4, 1),
    "rock_smash_mons": (60, 30, 5, 4, 1),
    "fishing_mons": (70, 30, 60, 20, 20, 40, 40, 15, 4, 1),
}
_RODS = {"old_rod": (0, 1), "good_rod": (2, 3, 4), "super_rod": (5, 6, 7, 8, 9)}
_SUFFIXES = {"ruby": "Ruby", "sapphire": "Sapphire", "firered": "FireRed", "leafgreen": "LeafGreen"}


@dataclass(frozen=True)
class WildTable:
    map_const: str
    label: str
    method: str
    rate: int
    slots: tuple[WildSlot, ...]


def wild_tables(repo: Gen3PretRepo, version: str) -> tuple[WildTable, ...]:
    if version not in dict(repo.versions):
        raise ValueError(f"{repo.root} : version inconnue {version}")
    path = repo.root / "src/data/wild_encounters.json"
    groups = read_json(path).get("wild_encounter_groups")
    if not isinstance(groups, list) or not 0 < len(groups) <= 16:
        raise ValueError(f"{path} : groupes sauvages invalides")
    result: list[WildTable] = []
    for group in groups:
        if group.get("for_maps") is False and group.get("label") in {
            "gBattlePyramidWildMonHeaders",
            "gBattlePikeWildMonHeaders",
        }:
            continue  # Séries des installations de combat : traitées dans la branche Hoenn.
        if group.get("for_maps") is not True or group.get("label") != "gWildMonHeaders":
            raise ValueError(f"{path} : groupe sauvage inconnu {group.get('label')}")
        _validate_fields(group.get("fields"), str(path))
        entries = group.get("encounters")
        if not isinstance(entries, list) or not 0 < len(entries) <= 1024:
            raise ValueError(f"{path} : rencontres invalides")
        for entry in entries:
            label = entry.get("base_label", "")
            if version in _SUFFIXES and not label.endswith("_" + _SUFFIXES[version]):
                if not any(label.endswith("_" + _SUFFIXES[other]) for other, _ in repo.versions):
                    raise ValueError(f"{path} : suffixe de version inconnu {label}")
                continue
            result.extend(_entry_tables(entry, str(path)))
    keys = [(table.map_const, table.label, table.method) for table in result]
    if not result or len(set(keys)) != len(keys):
        raise ValueError(f"{path} : tables absentes ou répétées pour {version}")
    return tuple(result)


def _validate_fields(fields: object, path: str) -> None:
    if not isinstance(fields, list) or len(fields) != len(_RATES):
        raise ValueError(f"{path} : champs sauvages invalides")
    seen: set[str] = set()
    for field in fields:
        kind = field.get("type")
        if kind not in _RATES or kind in seen or tuple(field.get("encounter_rates", ())) != _RATES[kind]:
            raise ValueError(f"{path} : probabilités moteur inconnues pour {kind}")
        seen.add(kind)
        if kind == "fishing_mons" and field.get("groups") != {key: list(value) for key, value in _RODS.items()}:
            raise ValueError(f"{path} : groupes de cannes inconnus")


def _entry_tables(entry: dict[str, Any], path: str) -> list[WildTable]:
    const, label = entry.get("map", ""), entry.get("base_label", "")
    if not re.fullmatch(r"MAP_\w+", const) or not label:
        raise ValueError(f"{path} : carte ou label sauvage invalide {entry}")
    if unknown := entry.keys() - {"map", "base_label", *_RATES}:
        raise ValueError(f"{path} : champs sauvages inconnus {unknown}")
    result = []
    for kind, rates in _RATES.items():
        if kind not in entry:
            continue
        row = entry[kind]
        rate = row.get("encounter_rate")
        mons = row.get("mons")
        if type(rate) is not int or not 0 < rate <= 100 or not isinstance(mons, list) or len(mons) != len(rates):
            raise ValueError(f"{path} : {label}/{kind} : taux ou nombre d'emplacements invalide")
        slots = tuple(_slot(mon, chance, f"{path} : {label}") for mon, chance in zip(mons, rates, strict=True))
        if kind == "fishing_mons":
            result += [
                WildTable(const, label, rod.replace("_", "-"), rate, tuple(slots[index] for index in indices))
                for rod, indices in _RODS.items()
            ]
        else:
            method = {"land_mons": "walk", "water_mons": "surf", "rock_smash_mons": "rock-smash"}[kind]
            if method == "surf" and const.startswith("MAP_UNDERWATER"):
                method = "seaweed"
            target = "MAP_ROUTE130_MIRAGE_ISLAND" if const == "MAP_ROUTE130" and method == "walk" else const
            table = WildTable(target, label, method, rate, slots)
            result.append(table)
    if const in {"MAP_SHOAL_CAVE_LOW_TIDE_ENTRANCE_ROOM", "MAP_SHOAL_CAVE_LOW_TIDE_INNER_ROOM"}:
        # Le script change le layout sans changer l'en-tête sauvage ; à marée basse il n'y a plus d'eau.
        result += [replace(table, map_const=const.replace("LOW_TIDE", "HIGH_TIDE")) for table in tuple(result)]
        result = [table for table in result if table.map_const != const or table.method == "walk"]
    return result


def _slot(mon: dict[str, Any], chance: int, path: str) -> WildSlot:
    species, low, high = mon.get("species", ""), mon.get("min_level"), mon.get("max_level")
    if (
        not re.fullmatch(r"SPECIES_[A-Z0-9_]+", species)
        or type(low) is not int
        or type(high) is not int
        or not 1 <= low <= high <= 100
    ):
        raise ValueError(f"{path} : emplacement sauvage invalide {mon}")
    return WildSlot(species.removeprefix("SPECIES_"), low, high, chance)


def roaming_maps(repo: Gen3PretRepo) -> tuple[str, ...]:
    text = repo.source_text("src/roamer.c", repo.versions[0][0])
    match = re.search(r"sRoamerLocations\[\]\[\d+\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not match:
        raise ValueError(f"{repo.root} : sRoamerLocations absent")
    body = match[1]
    if repo.ruby:
        numbers = {int(value, 16) for value in re.findall(r"0x([0-9A-Fa-f]+)", body)} - {255}
        maps = tuple(
            sorted(
                current.const for current in repo.maps.values() if current.group == 0 and current.group_index in numbers
            )
        )
        residue = re.sub(r"0x[0-9A-Fa-f]+|[{},\s]", "", body)
        if residue or len(maps) != len(numbers) or not 0 < len(maps) <= 64:
            raise ValueError(f"{repo.root} : routes errantes numériques invalides")
        return maps
    maps = tuple(sorted(set(re.findall(r"MAP_NUM\((MAP_\w+)\)", body))))
    residue = re.sub(r"MAP_NUM\(MAP_\w+\)|[{},\s]|___", "", body)
    if residue or not 0 < len(maps) <= 64 or any(const not in repo.maps for const in maps):
        raise ValueError(f"{repo.root} : routes errantes invalides : {residue}")
    return maps
