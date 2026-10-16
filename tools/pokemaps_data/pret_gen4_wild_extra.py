"""Listes sauvages hors des tables d'en-têtes (archive encdata_ex) : Barpau, arbres à Miel, Pokémon quotidiens du
Jardin Trophée et du Grand Marais.

Diamant/Perle versionnent l'archive extraite (files/arc/encdata_ex) ; Platine la compile depuis ses JSON
(res/field/encounters/encdata_ex.order et les scripts tools/jsoncnv/encdata_ex_*.py). Les deux lecteurs rendent les
membres numérotés de l'archive, espèces en numéros nationaux.
"""

from __future__ import annotations

from pathlib import Path

from .pret_gen4_narc import members
from .pret_gen4_source import ByteReader, metang_enum, read_binary, read_json, read_text

# Membres de l'archive, dans l'ordre de encdata_ex.order de Platine et de files/arc/encdata_ex de Diamant/Perle.
FEEBAS = 0
HONEY_FIRST = 2
TROPHY_GARDEN = 8
MARSH_NATIONAL = 9
MARSH_LOCAL = 10
_SIZES = {FEEBAS: 1, 2: 6, 3: 6, 4: 6, 5: 6, 6: 6, 7: 6, TROPHY_GARDEN: 16, MARSH_NATIONAL: 32, MARSH_LOCAL: 32}
_ORDER = (
    "encounters_mt_coronet_b1f_species.bin",
    "encounters_mt_coronet_b1f_tiles.bin",
    *("encounters_honey_tree_common.bin", "encounters_honey_tree_uncommon.bin", "encounters_honey_tree_rare.bin") * 2,
    "encounters_trophy_garden_dailies.bin",
    "encounters_great_marsh_lookout_natdex.bin",
    "encounters_great_marsh_lookout_local.bin",
    "encounters_great_marsh_lookout_coords.bin",
)


def read_wild_extra(root: Path, platinum: bool) -> dict[int, tuple[int, ...]]:
    """Membre de l'archive -> espèces, pour les membres d'espèces (les cases de Barpau et les coordonnées des jumelles
    ne sont pas lues : le moteur les tire selon la sauvegarde)."""
    result = _platinum(root) if platinum else _diamond_pearl(root)
    for member, size in _SIZES.items():
        species = result.get(member, ())
        if len(species) != size or not all(1 <= value <= 493 for value in species):
            raise ValueError(f"{root} : encdata_ex {member} : {size} espèces attendues, lu {species}")
    return result


def _diamond_pearl(root: Path) -> dict[int, tuple[int, ...]]:
    found = members(root / "files/arc/encdata_ex")
    if len(found) != len(_ORDER):
        raise ValueError(f"{root} : encdata_ex : {len(_ORDER)} membres attendus, {len(found)} lus")
    result = {}
    for member, size in _SIZES.items():
        path = found[member]
        reader = ByteReader(read_binary(path, 4 * size), str(path))
        if len(reader.data) != 4 * size:
            raise ValueError(f"{path} : {4 * size} octets attendus")
        result[member] = reader.unpack(f"{size}I", 0)
    return result


def _platinum(root: Path) -> dict[int, tuple[int, ...]]:
    folder = root / "res/field/encounters"
    if tuple(read_text(folder / "encdata_ex.order").split()) != _ORDER:
        raise ValueError(f"{folder}/encdata_ex.order : ordre de l'archive inconnu")
    species = metang_enum(root / "generated/species.txt")

    def values(names: object, where: str) -> tuple[int, ...]:
        if not isinstance(names, list) or any(name not in species for name in names):
            raise ValueError(f"{folder}/{where} : espèces inconnues : {names}")
        return tuple(species[name] for name in names)

    honey = read_json(folder / "encounters_honey_tree.json")
    marsh = read_json(folder / "encounters_great_marsh_lookout.json")
    coronet = read_json(folder / "encounters_mt_coronet_b1f.json")["elusive_rod_encounter"]
    result = {
        FEEBAS: values([coronet["species"]], "encounters_mt_coronet_b1f.json"),
        TROPHY_GARDEN: values(read_json(folder / "encounters_trophy_garden.json")["daily_encounters"], "trophy"),
        MARSH_NATIONAL: values(marsh["after_national_dex"], "marsh"),
        MARSH_LOCAL: values(marsh["before_national_dex"], "marsh"),
    }
    for offset, group in enumerate(("common", "uncommon", "rare")):
        result[HONEY_FIRST + offset] = result[HONEY_FIRST + 3 + offset] = values(honey[group], "honey")
    return result
