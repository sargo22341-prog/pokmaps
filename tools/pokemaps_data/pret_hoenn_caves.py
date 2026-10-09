"""Routes possibles des grottes à entrée mobile d'Émeraude, lues dans le moteur."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .pret_gen3_source import read_text

if TYPE_CHECKING:
    from .pret_gen3 import Gen3PretRepo


def moving_cave_areas(repo: Gen3PretRepo) -> tuple[tuple[str, str], ...]:
    if repo.ruby or repo.remake:
        return ()
    path = repo.root / "src/field_specials.c"
    text = read_text(path)
    tables = re.findall(r"sAbnormalWeatherMapNumbers\[\]\s*=\s*\{(.*?)\};", text, re.S)
    if len(tables) != 2:
        raise ValueError(f"{path} : deux tables de météo anormale attendues")
    routes = tuple(re.findall(r"MAP_NUM\((MAP_ROUTE\d+)\)", tables[0]))
    if len(routes) != 16 or routes != tuple(re.findall(r"MAP_NUM\((MAP_ROUTE\d+)\)", tables[1])):
        raise ValueError(f"{path} : routes des grottes mobiles incohérentes")
    if re.sub(r"MAP_NUM\(MAP_ROUTE\d+\)|[\s,]", "", tables[0]):
        raise ValueError(f"{path} : expression de route inconnue")
    result = []
    for area, entries in (("terra-cave/area", routes[:8]), ("marine-cave/area", routes[8:])):
        unique = tuple(dict.fromkeys(entries))
        if len(unique) != 4 or any(route not in repo.maps for route in unique):
            raise ValueError(f"{path} : quatre routes existantes attendues pour {area}")
        result.extend((route, area) for route in unique)
    return tuple(result)
