"""Rencontres natives HGSS projetées dans les tables communes, avec configurations exclusives."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .builder_wild_gen2 import WildEncounter
from .placement_hgss import read_placement_json
from .sources import PREVIEW_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder

REPLACED_METHODS = frozenset(
    {"walk", "surf", "old-rod", "good-rod", "super-rod", "rock-smash", "headbutt", "roaming-grass", "roaming-water"}
)
_PERIODS = {"morn": "time-morning", "day": "time-day", "nite": "time-night"}
_TREES = frozenset({"headbutt-common", "headbutt-rare", "headbutt-secret"})


@dataclass(frozen=True)
class HgssWildData:
    encounters: tuple[WildEncounter, ...]
    rates: tuple[tuple[int, int, int, int], ...]


def wild_data(builder: DatabaseBuilder) -> HgssWildData:
    catalog = read_placement_json(PREVIEW_DIR / "hgss-encounters/encounters.json")
    methods = {r["identifier"]: int(r["id"]) for r in builder.encounters.method_values}
    conditions = {r["identifier"]: int(r["id"]) for r in builder.encounters.condition_values}
    banks = {b["bank"]: b["headers"] for b in catalog["banks"]}
    retained = {row.header for row in builder.locations.native}
    encounters, rates = [], set()
    for table in catalog["distributions"] + catalog["headbutt"]:
        tree = table["method"] in _TREES
        headers = [table["bank"]] if tree else banks[table["bank"]]
        config = table["configuration"]
        keys = (
            ()
            if tree
            else (
                _PERIODS[config["period"]],
                f"radio-{config['radio']}",
                "swarm-yes" if config["swarm"] else "swarm-no",
            )
        )
        selected = tuple(sorted(conditions[key] for key in keys))
        method = methods[table["method"]]
        version = {"heartgold": 15, "soulsilver": 16}[table["version"]]
        for header in headers:
            if header not in retained or (header == 487 and table["method"] == "walk"):
                continue
            area = 30_000 + header
            for slot in table["slots"]:
                encounters.append(
                    WildEncounter(
                        version,
                        area,
                        slot["species"],
                        method,
                        selected,
                        slot["minimum"],
                        slot["maximum"],
                        slot["chance"],
                    )
                )
            if table["rate"] is not None:
                rates.add((version, area, method, table["rate"]))
    encounters.extend(_special(catalog, methods, conditions))
    encounters.extend(builder.encounters.hgss_safari.encounters)
    from .roamers_hgss import encounters as roaming_encounters

    encounters.extend(roaming_encounters(builder, methods))
    return HgssWildData(tuple(encounters), tuple(sorted(rates)))


def _special(catalog: dict, methods: dict[str, int], conditions: dict[str, int]) -> list[WildEncounter]:
    result = []
    special = catalog["special_wild"]
    for table in special["contest"]:
        keys = (
            "story-progress-national-dex" if table["national"] else "story-progress-before-national-dex",
            f"hgss-contest-{table['weekday']}",
        )
        selected = tuple(sorted(conditions[key] for key in keys))
        for version in (15, 16):
            result.extend(
                WildEncounter(
                    version, 30_487, s["species"], methods["walk"], selected, s["minimum"], s["maximum"], s["chance"]
                )
                for s in table["slots"]
            )
    return result
