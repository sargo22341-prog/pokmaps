"""Export de l'atlas HGSS qualifié vers les cartes et coordonnées communes Android."""

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from .maps import GameMapData, MapRow, SpotRow, WarpRow
from .maps_layout import identifier
from .placement_hgss import read_placement_json
from .preview_characters_hgss import check_characters
from .preview_placement_hgss import check_placement
from .sources import HGSS_PRET_COMMIT, PREVIEW_DIR
from .validate_maps_gen4 import write_inventory


def export_game(cache: Path, output: Path) -> GameMapData:
    source = PREVIEW_DIR / "hgss-maps/atlas"
    if (
        output.is_symlink()
        or output.name != "heartgold-soulsilver"
        or source.resolve().is_relative_to(output.resolve())
    ):
        raise ValueError(f"HGSS : destination d'export invalide : {output}")
    catalog = read_placement_json(source / "catalog.json")
    if catalog["commit"] != HGSS_PRET_COMMIT:
        raise ValueError("HGSS : atlas d'un autre commit")
    placement = check_placement(PREVIEW_DIR / "hgss-placement")
    characters = check_characters(PREVIEW_DIR / "hgss-characters")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    from .plans_application_hgss import application_catalog, native_map_types

    catalog = application_catalog(catalog, native_map_types(cache / "hgss-qualification"))
    rows, offsets = _maps(source, output, catalog, cache / "hgss-qualification")
    print(f"HGSS : {len(rows)} cartes et niveaux exportés", flush=True)
    lookup = {row["header"]: row for row in catalog["maps"]}
    areas = [(row["const"], "hgss-" + identifier(row["const"])) for row in catalog["maps"]]
    areas.extend(_api_areas(catalog))
    data = GameMapData(rows, areas, _warps(catalog, lookup), [], coordinate_offsets=offsets)
    from .passages_guide_hgss import script_passages

    data.warps.extend(script_passages(cache / "hgss-qualification", lookup, offsets))
    _spots(data, placement, lookup, offsets)
    _editor_assets(output, data, lookup, offsets)
    from .maps_characters_hgss import character_rows

    data.objects = character_rows(cache / "hgss-qualification", characters, lookup, offsets, output)
    print(f"HGSS : {len(data.objects)} repères exportés", flush=True)
    from .passages_characters_hgss import clear_passages

    clear_passages(data, cache / "hgss-qualification", lookup, offsets)
    payload = dict(
        commit=HGSS_PRET_COMMIT,
        maps=[asdict(row) for row in rows],
        passages=[asdict(row) for row in data.warps],
        source_catalog=catalog,
    )
    (output / "catalog.json").write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    write_inventory(output)
    return data


def _editor_assets(output: Path, data: GameMapData, lookup: dict, offsets: dict) -> None:
    rows = {r["const"]: dict(native=r["const"], offset=offsets[identifier(r["const"])]) for r in lookup.values()}
    (output / "assemblies.json").write_text(json.dumps(rows, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    terrain = {identifier(r["const"]): dict(scope=r["scope"], terrain={}) for r in lookup.values()}
    for (const, kind), points in data.terrain.items():
        terrain[const]["terrain"][kind] = sorted(points)
    (output / "terrain.json").write_text(json.dumps(terrain, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _maps(source: Path, output: Path, catalog: dict, root: Path) -> tuple[list[MapRow], dict[str, tuple[int, int]]]:
    rows, offsets = [], {}
    plans = {p["id"]: p for p in catalog["plans"]}
    names = {
        "johto-exterieurs": ("JOHTO", 993, "Johto et Kanto", "MAP_NEW_BARK"),
        "kanto-exterieurs": ("KANTO", 992, "Kanto", "MAP_PALLET"),
    }
    for plan in catalog["plans"]:
        if plan.get("standalone"):
            continue
        number = 540 + sum(not row.is_world for row in rows)
        const, number, name, start = names.get(plan["id"], (plan["id"], number, plan["name_fr"], None))
        rows.append(
            MapRow(
                const,
                number,
                name,
                None,
                0,
                0,
                *plan["size"],
                plan["level_count"],
                is_world=start is not None,
                start=start,
            )
        )
        _write_plan(source, output, catalog, plan, const, root)
    for record in catalog["maps"]:
        plan = plans[record["plan"]]
        parent = names.get(plan["id"], (plan["id"],))[0]
        offset = next(tuple(p["offset"]) for p in plan["parts"] if p["header"] == record["header"])
        offsets[identifier(record["const"])] = offset
        rows.append(_native_map(source, output, record, plan, parent, offset))
    from .origins_hgss import assign_origins

    assign_origins(rows, catalog)
    return rows, offsets


def _native_map(source: Path, output: Path, record: dict, plan: dict, parent: str, offset: tuple) -> MapRow:
    standalone = plan.get("standalone", False)
    if standalone:
        from .maps_plans_hgss import write_plan

        write_plan(source, [record], output / identifier(record["const"]))
    return MapRow(
        record["const"],
        record["header"],
        record["name_fr"],
        None if standalone else parent,
        *offset,
        *record["size"],
        plan["level_count"] if standalone else 0,
    )


def _write_plan(source: Path, output: Path, catalog: dict, plan: dict, const: str, root: Path) -> None:
    if plan.get("unified"):
        from .worlds_application_hgss import write_world

        members = [r for r in catalog["maps"] if r["plan"] == plan["id"]]
        write_world(source, output / identifier(const), members, root)
    elif plan.get("separated"):
        from .maps_plans_hgss import write_plan

        members = [r for r in catalog["maps"] if r["plan"] == plan["id"]]
        write_plan(source, members, output / identifier(const))
    else:
        shutil.copytree(source / "plans" / plan["id"], output / identifier(const))


def _warps(catalog: dict, lookup: dict[int, dict]) -> list[WarpRow]:
    from .layers_application_hgss import surface_map
    from .passages_guide_hgss import excluded_passages

    result = []
    excluded = excluded_passages(catalog)
    for passage in catalog["passages"]:
        if (passage["source"], passage["index"]) in excluded:
            continue
        target = lookup.get(passage["destination"])
        arrival = passage.get("target_pixel", (None, None)) if target else (None, None)
        result.append(
            WarpRow(
                surface_map(lookup[passage["source"]], passage["source_surface"]["height_fx32"]),
                *passage["source_pixel"],
                surface_map(target, passage["target_surface"]["height_fx32"]) if target else None,
                *arrival,
            )
        )
    return result


def _spots(data: GameMapData, placement: dict, lookup: dict, offsets: dict) -> None:
    excluded = {(r["header"], r["kind"]) for r in placement["coverage"] if r["reason"]}
    for record in placement["catalog"]["maps"]:
        const = lookup[record["header"]]["const"]
        dx, dy = offsets[identifier(const)]
        for kind, points in record["terrain"].items():
            data.terrain[(identifier(const), kind)] = frozenset((x + dx, y + dy) for x, y in points)
            if (record["header"], kind) not in excluded:
                data.spots.extend(SpotRow(const, kind, x + dx, y + dy) for x, y in points)


def _api_areas(catalog: dict) -> list[tuple[str, str]]:
    import csv

    from .sources import DATA_DIR

    known = {row["const"] for row in catalog["maps"]}
    with (DATA_DIR / "hgss_area_bindings.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if any(row["map"] not in known or not row["reason"] for row in rows):
        raise ValueError("HGSS : rattachement de zone inconnu ou sans justification")
    return [(row["map"], row["area"]) for row in rows]
