"""Tables de rencontres DS au format du moteur (424 octets), lues telles quelles, sans interprétation.

Diamant/Perle versionnent les tables compilées (encountdata/d_enc_data, p_enc_data) ; Platine les écrit en JSON,
compilées par tools/jsoncnv/encounter.py dans le même ordre. Les deux sources donnent ici la même structure,
espèces en numéros nationaux. Le sens des emplacements, taux et remplacements est lu en phase 4.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

from .pret_gen4_narc import FIELD_DATA, members
from .pret_gen4_source import ByteReader, metang_enum, read_binary, read_json

TABLE_SIZE = 424
LAND_SLOTS = 12
WATER_SLOTS = 5
GBA_VERSIONS = ("ruby", "sapphire", "emerald", "firered", "leafgreen")
_WATER_PADDING = 44
_FORM_RATES = ("rate_form0", "rate_form1", "rate_form2", "rate_form3", "rate_form4", "unown_table")
_RODS = ("old", "good", "super")
# Clés des JSON de Platine compilées ailleurs (encdata_ex) ou purement descriptives : hors de la table de
# 424 octets, elles sont lues avec les rencontres particulières (phase 4).
_OUTSIDE_TABLE = frozenset({"map_category", "elusive_rod_encounter", "daily_encounters"})


@dataclass(frozen=True)
class WaterSlot:
    level_max: int
    level_min: int
    species: int


@dataclass(frozen=True)
class EncounterTable:
    land_rate: int
    land: tuple[tuple[int, int], ...]  # (niveau, espèce) des 12 emplacements
    swarms: tuple[int, int]
    day: tuple[int, int]
    night: tuple[int, int]
    radar: tuple[int, int, int, int]
    form_rates: tuple[int, ...]  # rate_form0 à rate_form4, puis unown_table
    gba: tuple[tuple[str, tuple[int, int]], ...]
    surf_rate: int
    surf: tuple[WaterSlot, ...]
    rods: tuple[tuple[str, int, tuple[WaterSlot, ...]], ...]  # (canne, taux, emplacements)

    def __post_init__(self) -> None:
        if len(self.land) != LAND_SLOTS or len(self.surf) != WATER_SLOTS:
            raise ValueError("table de rencontres : nombre d'emplacements invalide")
        if any(len(slots) != WATER_SLOTS for _, _, slots in self.rods):
            raise ValueError("table de rencontres : nombre d'emplacements de pêche invalide")


def read_dp_encounters(root: Path) -> dict[str, dict[int, EncounterTable]]:
    """Tables de Diamant (d_enc_data) et de Perle (p_enc_data), par version puis par numéro."""
    tables: dict[str, dict[int, EncounterTable]] = {}
    for version, folder in (("diamond", "d_enc_data"), ("pearl", "p_enc_data")):
        tables[version] = {
            index: compiled_table(ByteReader(read_binary(path, TABLE_SIZE), str(path)))
            for index, path in members(root / FIELD_DATA / "encountdata" / folder).items()
        }
    return tables


def compiled_table(reader: ByteReader) -> EncounterTable:
    """Table compilée : taux et 12 emplacements d'herbe, remplacements, taux de formes, double insertion, surf,
    44 octets nuls, puis taux et emplacements de chaque canne (offsets de tools/jsoncnv/encounter.py)."""
    if len(reader.data) != TABLE_SIZE:
        raise ValueError(f"{reader.where} : table de {len(reader.data)} octets, {TABLE_SIZE} attendus")
    words = reader.unpack("51I", 0)
    gba = reader.unpack("10I", 164)
    if any(reader.slice(248, _WATER_PADDING)):
        raise ValueError(f"{reader.where} : remplissage non nul après le surf")
    return EncounterTable(
        land_rate=words[0],
        land=tuple((words[1 + 2 * i], words[2 + 2 * i]) for i in range(LAND_SLOTS)),
        swarms=(words[25], words[26]),
        day=(words[27], words[28]),
        night=(words[29], words[30]),
        radar=(words[31], words[32], words[33], words[34]),
        form_rates=tuple(words[35:41]),
        gba=tuple((version, (gba[2 * i], gba[2 * i + 1])) for i, version in enumerate(GBA_VERSIONS)),
        surf_rate=reader.u32(204),
        surf=_water(reader, 208),
        rods=tuple((rod, reader.u32(292 + 44 * i), _water(reader, 296 + 44 * i)) for i, rod in enumerate(_RODS)),
    )


def _water(reader: ByteReader, offset: int) -> tuple[WaterSlot, ...]:
    slots = []
    for i in range(WATER_SLOTS):
        level_max, level_min, padding, species = reader.unpack("BBHI", offset + 8 * i)
        if padding:
            raise ValueError(f"{reader.where} : remplissage non nul à {offset + 8 * i:#x}")
        slots.append(WaterSlot(level_max, level_min, species))
    return tuple(slots)


def read_platinum_encounters(root: Path, order: dict[str, int]) -> dict[int, EncounterTable]:
    """Tables JSON de Platine, numérotées selon encounters.order."""
    species = metang_enum(root / "generated/species.txt")
    return {
        index: json_table(read_json(root / f"res/field/encounters/{name}.json"), species, name)
        for name, index in order.items()
    }


def json_table(data: dict, species: dict[str, int], where: str) -> EncounterTable:
    expected = {
        "land_rate",
        "land_encounters",
        "swarms",
        "day",
        "night",
        "radar",
        *_FORM_RATES,
        *GBA_VERSIONS,
        "surf_rate",
        "surf_encounters",
        *(f"{rod}_rod_{part}" for rod, part in itertools.product(_RODS, ("rate", "encounters"))),
    }
    if missing := expected - set(data):
        raise ValueError(f"{where} : champs de rencontres absents : {sorted(missing)}")
    if unknown := set(data) - expected - _OUTSIDE_TABLE:
        raise ValueError(f"{where} : champs de rencontres inconnus : {sorted(unknown)}")

    def mon(name: str) -> int:
        if name not in species:
            raise ValueError(f"{where} : espèce inconnue : {name}")
        return species[name]

    def two(key: str) -> tuple[int, int]:
        if len(data[key]) != 2:
            raise ValueError(f"{where} : deux espèces attendues pour {key}")
        return (mon(data[key][0]), mon(data[key][1]))

    def water(key: str) -> tuple[WaterSlot, ...]:
        return tuple(WaterSlot(s["level_max"], s["level_min"], mon(s["species"])) for s in data[key])

    land = data["land_encounters"]
    radar = [mon(name) for name in data["radar"]]
    if len(radar) != 4:
        raise ValueError(f"{where} : quatre espèces de Pokéradar attendues")
    return EncounterTable(
        land_rate=data["land_rate"],
        land=tuple((slot["level"], mon(slot["species"])) for slot in land),
        swarms=two("swarms"),
        day=two("day"),
        night=two("night"),
        radar=(radar[0], radar[1], radar[2], radar[3]),
        form_rates=tuple(data[key] for key in _FORM_RATES),
        gba=tuple((version, two(version)) for version in GBA_VERSIONS),
        surf_rate=data["surf_rate"],
        surf=water("surf_encounters"),
        rods=tuple((rod, data[f"{rod}_rod_rate"], water(f"{rod}_rod_encounters")) for rod in _RODS),
    )
