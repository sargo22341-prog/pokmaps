"""Routes natives des quatre errants HGSS, séparées par région et version."""

import re
from typing import TYPE_CHECKING

from .builder_wild_gen2 import WildEncounter
from .placement_hgss import read_placement_json
from .sources import PREVIEW_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder


def encounters(builder: DatabaseBuilder, methods: dict[str, int]) -> list[WildEncounter]:
    root = builder.pret_roots["heartgold-soulsilver"]
    source = (root / "src/field_roamer.c").read_text(encoding="utf-8")
    table = source.split("sRoamerLocations[ROAMER_LOC_COUNT] = {", 1)[1].split("};", 1)[0]
    johto, kanto = table.split("// Kanto", 1)
    regions = [re.findall(r"MAP_ROUTE_\d+", part) for part in (johto, kanto)]
    if [len(rows) for rows in regions] != [16, 25]:
        raise ValueError("HGSS : routes des errants natives inattendues")
    locations = {row.identifier: row for row in builder.locations.native}
    catalog = read_placement_json(PREVIEW_DIR / "hgss-encounters/encounters.json")
    banks = {bank["bank"]: bank["headers"] for bank in catalog["banks"]}
    available = {
        (header, row["method"]) for row in catalog["distributions"] for header in banks[row["bank"]] if row["rate"]
    }
    result = []
    for region, routes in enumerate(regions):
        for route in routes:
            identifier = "hgss-" + route.removeprefix("MAP_").lower().replace("_", "-")
            area = locations[identifier].area_id
            species = ((15, 243, 40), (16, 243, 40), (15, 244, 40), (16, 244, 40))
            if region == 1:
                species = ((15, 380, 35), (16, 381, 35))
            for version, pokemon, level in species:
                for method in ("roaming-grass", "roaming-water"):
                    ordinary = "walk" if method == "roaming-grass" else "surf"
                    if (locations[identifier].header, ordinary) not in available:
                        continue
                    result.append(WildEncounter(version, area, pokemon, methods[method], (), level, level, 1))
    return result
