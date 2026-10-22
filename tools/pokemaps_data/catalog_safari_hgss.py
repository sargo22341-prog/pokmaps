"""Gabarits et configurations natives du Safari HGSS, sans arrangement universel inventé."""

import re

from .pret_gen4_source import c_defines, read_text
from .pret_hgss_maps import HgssMapRepo


def safari_catalog(repo: HgssMapRepo) -> dict:
    source = "src/safari_zone.c"
    constants = c_defines(repo.root / "include/constants/safari.h", "SAFARI_ZONE_AREA_")
    text = read_text(repo.root / source)
    match = re.search(
        r"sSafariZoneDefaultAreaSets\[10\]\[SAFARI_ZONE_MAX_AREAS_PER_SET\] = \{(.*?)\n\};", text, re.DOTALL
    )
    if match is None:
        raise ValueError(f"{source} : configurations initiales du Safari absentes")
    sets = [
        [constants[name] for name in re.findall(r"SAFARI_ZONE_AREA_\w+", row)]
        for row in re.findall(r"\{([^{}]+)\}", match[1])
    ]
    if len(sets) != 10 or any(len(s) != 6 or len(set(s)) != 6 or any(a not in range(12) for a in s) for s in sets):
        raise ValueError(f"{source} : configurations initiales du Safari invalides")
    templates = []
    for area in range(12):
        blocks = repo.blocks(repo.headers[343 + area])
        if len(blocks) != 1 or blocks[0][2] != 652 + area:
            raise ValueError(f"Safari : gabarit natif incohérent pour l'habitat {area}")
        templates.append(dict(area=area, header=343 + area, block=652 + area))
    return {
        "runtime_header": 357,
        "matrix": 212,
        "slots": [dict(column=x + 1, row=z + 1) for z in range(2) for x in range(3)],
        "templates": templates,
        "initial_sets": sets,
        "sources": [source, "src/map_matrix.c", "include/constants/safari.h"],
        "selection": "Six habitats configurés dans le jeu ; aucune configuration universelle",
    }
