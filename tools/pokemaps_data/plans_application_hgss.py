"""Plans Android HGSS : seules les salles reliées partagent une vue intérieure."""

from collections import defaultdict
from copy import deepcopy
from pathlib import Path

from .maps_layout import identifier
from .maps_plans_hgss import plan_layout
from .maps_render import level_count
from .pret_hgss_maps import HgssMapRepo
from .worlds_application_hgss import WORLD_PLANS, merge_worlds


def native_map_types(root: Path) -> dict[int, str]:
    return {h.index: dict(h.fields)["mapType"] for h in HgssMapRepo(root, "heartgold").headers.values()}


def application_catalog(source: dict, map_types: dict[int, str]) -> dict:
    catalog = deepcopy(source)
    records = {r["header"]: r for r in catalog["maps"]}
    reachable = _world_connected(source, records)
    previous = {p["header"]: p["offset"] for plan in source["plans"] for p in plan["parts"]}
    merge_worlds(catalog)
    links: dict[int, set[int]] = defaultdict(set)
    for passage in source["passages"]:
        start, end = passage["source"], passage["destination"]
        if end in records and records[start]["plan"] == records[end]["plan"] and map_types[start] == map_types[end]:
            links[start].add(end)
            links[end].add(start)
    plans = []
    for plan in catalog["plans"]:
        if plan["id"] in WORLD_PLANS:
            plans.append(deepcopy(plan))
            continue
        groups = _connected_rooms({p["header"] for p in plan["parts"]}, links)
        for group in groups:
            members = [records[h] for h in sorted(group)]
            name = _plan_identifier(plan["id"], members, len(groups))
            standalone = len(members) == 1 and members[0]["header"] in reachable
            if len(members) == 1 and not standalone:
                name = identifier(members[0]["const"]) + "-plan"
            for record in members:
                record["plan"] = name
            size, parts = plan_layout(members)
            plans.append(
                dict(
                    id=name,
                    name_fr=members[0]["name_fr"],
                    size=size,
                    parts=parts,
                    level_count=level_count(*size),
                    layout="atlas",
                    separated=True,
                    standalone=standalone,
                )
            )
    catalog["plans"] = plans
    offsets = {p["header"]: p["offset"] for plan in plans for p in plan["parts"]}
    for passage in catalog["passages"]:
        for side, field in (("source", "source"), ("target", "destination")):
            header = passage[field]
            if f"{side}_pixel" not in passage or header not in records:
                continue
            passage[f"{side}_pixel"] = [
                value - previous[header][axis] + offsets[header][axis]
                for axis, value in enumerate(passage[f"{side}_pixel"])
            ]
            passage[f"{side}_plan"] = records[header]["plan"]
    return catalog


def _world_connected(source: dict, records: dict) -> set[int]:
    reached = {h for h, record in records.items() if record["plan"] in WORLD_PLANS}
    edges = [(p["source"], p.get("destination")) for p in source["passages"] + source.get("script_navigation", [])]
    for _ in range(len(records)):
        expanded = reached | {b for a, b in edges if a in reached and b in records}
        expanded.update(a for a, b in edges if b in reached)
        if expanded == reached:
            break
        reached = expanded
    return reached


def _plan_identifier(original: str, members: list[dict], groups: int) -> str:
    if len(members) == 1:
        return members[0]["const"]
    if groups == 1:
        return original
    building, floor = original.rsplit("-", 1)
    return f"{building}-rooms-{members[0]['header']}-{floor}"


def _connected_rooms(headers: set[int], links: dict[int, set[int]]) -> list[set[int]]:
    remaining = set(headers)
    groups = []
    for _ in range(len(headers)):
        if not remaining:
            break
        group = {min(remaining)}
        for _ in range(len(headers)):
            expanded = group | {neighbor for header in group for neighbor in links[header] if neighbor in headers}
            if expanded == group:
                break
            group = expanded
        remaining -= group
        groups.append(group)
    return groups
