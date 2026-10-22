"""Tables HGSS : ordre essaim/radio et nuit/essaim du moteur encounter_check.c."""

import re
from dataclasses import replace
from pathlib import Path

from .encounters_hgss import Configuration, Distribution, Period, Radio, Slot, configurations
from .pret_gen4_source import c_defines, read_json, read_text
from .pret_hgss_maps import HgssMapRepo

WILD_SOURCE = "files/fielddata/encountdata/gs_enc_data.json"
TREE_SOURCE = "files/arc/headbutt.json"
_LAND = (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1)
_SURF = (60, 30, 5, 4, 1)
_FISH = (40, 30, 15, 10, 5)
_ROCK = (80, 20)
_TREE = (50, 15, 15, 10, 5, 5)


def variant(value: object, version: str) -> object:
    if not isinstance(value, dict):
        return value
    if set(value) == {"gold", "silver"}:
        return value["gold" if version == "heartgold" else "silver"]
    if set(value) != {"HEARTGOLD", "SOULSILVER"}:
        raise ValueError(f"HGSS : variante inconnue : {value}")
    return value[version.upper()]


def _species(value: object, version: str, species: dict[str, int]) -> int:
    name = variant(value, version)
    if not isinstance(name, str) or name not in species or not 1 <= species[name] <= 493:
        raise ValueError(f"HGSS : espèce inconnue : {name}")
    return species[name]


def _slots(data: dict, method: str, version: str, config: Configuration, species: dict[str, int]) -> list[Slot]:
    weights = _LAND if method == "walk" else _ROCK if method == "rock-smash" else _SURF if method == "surf" else _FISH
    if len(data["mons"]) != len(weights):
        raise ValueError(f"HGSS {method} : nombre d'emplacements invalide")
    result = []
    for mon, chance in zip(data["mons"], weights, strict=True):
        name = mon["species"][config.period.value] if method == "walk" else mon["species"]
        level = mon["level"]
        low = variant(level, version) if method == "walk" else variant(level["min"], version)
        high = low if method == "walk" else variant(level["max"], version)
        result.append(Slot(_species(name, version, species), int(low), int(high), chance))
    return result


def _replace_species(slots: list[Slot], indices: tuple[int, ...], value: object, version: str, species: dict) -> None:
    number = _species(value, version, species)
    for index in indices:
        slots[index] = replace(slots[index], species=number)


def distribution(
    data: dict, bank: int, method: str, version: str, config: Configuration, species: dict[str, int], swarm: int | None
) -> Distribution | None:
    key = method.replace("-", "_")
    table = data["land"] if method == "walk" else data["fishing"][key] if "rod" in method else data[key]
    if not table["rate"]:
        if table["mons"]:
            raise ValueError(f"HGSS {bank}/{method} : emplacements avec taux nul")
        return None
    slots = _slots(table, method, version, config, species)
    if method == "walk":
        if config.swarm and swarm == 0:
            _replace_species(slots, (0, 1), data["landSwarm"], version, species)
        if config.radio is not Radio.OFF:
            sounds = data[config.radio.value]
            if len(sounds) != 2:
                raise ValueError(f"HGSS {bank} : table radio absente")
            for indices, value in zip(((2, 3), (4, 5)), sounds, strict=True):
                _replace_species(slots, indices, value, version, species)
    elif method == "surf" and config.swarm and swarm == 1:
        _replace_species(slots, (0,), data["surfSwarm"], version, species)
    elif "rod" in method:
        _fishing(slots, data, method, version, config, species, swarm)
    return Distribution(version, bank, method, config, table["rate"], tuple(slots))


def _fishing(
    slots: list[Slot], data: dict, method: str, version: str, config: Configuration, species: dict, swarm: int | None
) -> None:
    if config.period is Period.NIGHT and method in ("good-rod", "super-rod"):
        _replace_species(slots, (3 if method == "good-rod" else 1,), data["nightFish"], version, species)
    if config.swarm and swarm == 2:
        indices = {"old-rod": (2,), "good-rod": (0, 2, 3), "super-rod": (0, 1, 2, 3, 4)}[method]
        _replace_species(slots, indices, data["fishSwarm"], version, species)


def swarm_banks(repo: HgssMapRepo, banks: dict[str, int]) -> dict[int, int]:
    source = read_text(repo.root / "src/unk_02097F6C.c")
    entries = re.findall(r"\{\s*(MAP_\w+),\s*([012])\s*\}", source)
    if len(entries) != 20 or len(set(entries)) != 20:
        raise ValueError("HGSS : vingt lieux d'essaim attendus")
    headers = {header.constant: header for header in repo.headers.values()}
    return {banks[dict(headers[name].fields)["wildEncounterBank"]]: int(kind) for name, kind in entries}


def read_wild(root: Path) -> tuple[tuple[Distribution, ...], dict[int, tuple[int, ...]]]:
    raw = read_json(root / WILD_SOURCE)["encounters"]
    if len(raw) != 142 or len({r["map"] for r in raw}) != 142:
        raise ValueError("HGSS : 142 banques sauvages uniques attendues")
    banks = {
        "ENCDATA_UNUSED_090" if row["map"] == "090" else f"ENCDATA_{row['map']}": index for index, row in enumerate(raw)
    }
    declarations = re.findall(
        r"#define\s+(ENCDATA_\w+)\s+ENCDATA\(_(\d+)\)", read_text(root / "include/encounter_tables_narc.h")
    )
    declared = {name: int(index) for name, index in declarations}
    # Le dernier identifiant technique n'a pas de membre JSON ; la banque 90 porte un nom abrégé dans le JSON.
    if declared.pop("ENCDATA_UNUSED_142", None) != 142 or declared != banks:
        raise ValueError("HGSS : ordre des banques différent de l'index natif")
    repo = HgssMapRepo(root, "heartgold")
    for header in repo.headers.values():
        bank = dict(header.fields)["wildEncounterBank"]
        if bank != "ENCDATA_NA" and bank not in banks:
            raise ValueError(f"HGSS {header.constant} : banque sauvage inconnue : {bank}")
    for port in (386, 387):
        if dict(repo.headers[port].fields)["wildEncounterBank"] != "ENCDATA_NA":
            raise ValueError(f"HGSS {port} : le quai de Carmin possède maintenant une table sauvage")
    swarms = swarm_banks(repo, banks)
    headers: dict[int, tuple[int, ...]] = {}
    for index in range(len(raw)):
        headers[index] = tuple(
            h.index
            for h in repo.headers.values()
            if dict(h.fields)["wildEncounterBank"] in banks and banks[dict(h.fields)["wildEncounterBank"]] == index
        )
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    tables = []
    for version in ("heartgold", "soulsilver"):
        for bank, data in enumerate(raw):
            for config in configurations():
                for method in ("walk", "surf", "old-rod", "good-rod", "super-rod", "rock-smash"):
                    result = distribution(data, bank, method, version, config, species, swarms.get(bank))
                    if result is not None:
                        tables.append(result)
    return tuple(tables), headers


def read_trees(root: Path) -> tuple[Distribution, ...]:
    raw = read_json(root / TREE_SOURCE)["tables"]
    if len(raw) != 540:
        raise ValueError("HGSS : 540 tables d'arbres attendues")
    species = c_defines(root / "include/constants/species.h", "SPECIES_")
    tables = []
    for header, data in enumerate(raw):
        for key, method in (("CommonMons", "common"), ("RareMons", "rare"), ("SecretMons", "secret")):
            mons = data[key]
            if not mons:
                continue
            for version in ("heartgold", "soulsilver"):
                slots = tuple(
                    Slot(
                        _species(m["species"], version, species),
                        int(variant(m["minLevel"], version)),
                        int(variant(m["maxLevel"], version)),
                        chance,
                    )
                    for m, chance in zip(mons, _TREE, strict=True)
                )
                tables.append(Distribution(version, header, f"headbutt-{method}", Configuration(), None, slots))
    return tuple(tables)
