"""Positions initiales des décors créés par les mécanismes d'arènes HGSS."""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HgssDynamicProp:
    header: int
    model: int
    position: tuple[int, int, int]
    rotation_y: int
    source: str
    reason: str


def read_dynamic_props() -> tuple[HgssDynamicProp, ...]:
    path = Path(__file__).resolve().parents[1] / "data/hgss_dynamic_props.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    if not 1 <= len(rows) <= 64:
        raise ValueError(f"{path} : nombre de décors dynamiques HGSS invalide")
    props = tuple(
        HgssDynamicProp(
            int(r["header"]),
            int(r["model"]),
            tuple(int(r[k]) for k in ("x", "y", "z")),
            int(r["rotation_y"]),
            r["source"],
            r["reason"],
        )
        for r in rows
    )
    if len(set(props)) != len(props):
        raise ValueError(f"{path} : décor dynamique HGSS dupliqué")
    for prop in props:
        if (
            not 0 <= prop.header < 540
            or not 0 <= prop.model < 1024
            or any(not -8192 <= value <= 8192 for value in prop.position)
            or prop.rotation_y not in (0, 16384, 32768, 49152)
            or not prop.reason
            or not prop.source.startswith("src/field/gymmick/")
            or ".." in prop.source
        ):
            raise ValueError(f"{path} : décor dynamique HGSS invalide : {prop}")
    return props
