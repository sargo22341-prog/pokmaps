"""Carte commune Johto–Kanto, placée dans le repère de la matrice native HGSS."""

from pathlib import Path

from .maps_plans_hgss import plan_layout, write_plan
from .maps_render import level_count
from .maps_render_hgss import HgssRenderer
from .pret_hgss_maps import HgssMapRepo

WORLD_PLANS = frozenset({"johto-exterieurs", "kanto-exterieurs"})


def merge_worlds(catalog: dict) -> None:
    worlds = [plan for plan in catalog["plans"] if plan["id"] in WORLD_PLANS]
    if len(worlds) != 2:
        return
    records = [record for record in catalog["maps"] if record["plan"] in WORLD_PLANS]
    for record in records:
        record["plan"] = "johto-exterieurs"
    size, parts = plan_layout(records)
    merged = dict(
        id="johto-exterieurs",
        name_fr="Johto et Kanto",
        size=size,
        parts=parts,
        level_count=level_count(*size),
        layout="native",
        unified=True,
    )
    catalog["plans"] = [merged] + [plan for plan in catalog["plans"] if plan["id"] not in WORLD_PLANS]


def write_world(source: Path, output: Path, records: list[dict], root: Path) -> None:
    renderer = HgssRenderer(HgssMapRepo(root, "heartgold"))
    write_plan(source, records, output, renderer)
