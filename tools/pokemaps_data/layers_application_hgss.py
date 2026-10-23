"""Plans inférieurs HGSS alignés sur leur plan supérieur, compatibles avec les sélecteurs Android."""

from pathlib import Path

from PIL import Image

from .maps import MapRow
from .maps_layout import identifier
from .maps_plans_hgss import _paste_tiles, _reduce_tiles


def plan_const(plan: str) -> str:
    return {"johto-exterieurs": "JOHTO", "kanto-exterieurs": "KANTO"}.get(plan, plan)


def layer_const(plan: str, depth: int) -> str:
    return plan_const(plan) + ("_LOWER" if depth == 1 else f"_LOWER_{depth}")


def actor_layer(record: dict, ceiling: int) -> str:
    if record["plan"] in {"johto-exterieurs", "kanto-exterieurs"}:
        return record["const"]
    layers = sorted(record["layers"], key=lambda r: r["ceiling_fx32"], reverse=True)
    depth = next(i for i, row in enumerate(layers, 1) if row["ceiling_fx32"] == ceiling)
    return layer_const(record["plan"], depth)


def surface_map(record: dict, height: int) -> str:
    if record["plan"] in {"johto-exterieurs", "kanto-exterieurs"}:
        return record["const"]
    candidates = [row for row in record["layers"] if height < row["ceiling_fx32"]]
    if not candidates:
        return record["const"]
    return actor_layer(record, min(candidates, key=lambda r: r["ceiling_fx32"])["ceiling_fx32"])


def write_layers(source: Path, output: Path, catalog: dict, rows: list[MapRow]) -> None:
    records = {r["header"]: r for r in catalog["maps"]}
    number = max((r.number for r in rows if 540 <= r.number < 992), default=539) + 1
    for plan in catalog["plans"]:
        if plan["id"] in {"johto-exterieurs", "kanto-exterieurs"}:
            continue
        parts = [(records[p["header"]], p["offset"]) for p in plan["parts"]]
        count = max(len(r["layers"]) for r, _ in parts)
        upper = next(row for row in rows if row.const == plan_const(plan["id"]))
        for depth in range(1, count + 1):
            const = layer_const(plan["id"], depth)
            folder = output / identifier(const)
            folder.mkdir()
            for record, offset in parts:
                layers = sorted(record["layers"], key=lambda r: r["ceiling_fx32"], reverse=True)
                selected = layers[depth - 1] if len(layers) >= depth else record
                with Image.open(source / selected["image"]) as image:
                    _paste_tiles(image.convert("RGBA"), tuple(offset), folder / str(plan["level_count"] - 1))
            for level in range(plan["level_count"] - 2, -1, -1):
                _reduce_tiles(folder / str(level + 1), folder / str(level))
            rows.append(
                MapRow(
                    const,
                    number,
                    plan["name_fr"] + f" — niveau inférieur {depth}",
                    None,
                    0,
                    0,
                    *plan["size"],
                    plan["level_count"],
                    origin=upper.start or upper.origin,
                )
            )
            number += 1
    if number >= 992:
        raise ValueError("HGSS : trop de plans pour les identifiants composites")
