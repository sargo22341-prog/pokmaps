"""Origines géographiques des plans HGSS depuis les portes et déplacements natifs."""

from collections import defaultdict, deque

from .maps import MapRow


def assign_origins(rows: list[MapRow], catalog: dict) -> None:
    native = {record["header"]: record for record in catalog["maps"]}
    outside = {number for number, r in native.items() if r["plan"] in {"johto-exterieurs", "kanto-exterieurs"}}
    links: dict[int, set[int]] = defaultdict(set)
    for passage in catalog["passages"] + catalog["script_navigation"]:
        source, target = passage["source"], passage.get("destination")
        if target in native:
            links[source].add(target)
            links[target].add(source)
    for row in rows:
        if row.parent is not None or row.is_world or row.origin is not None:
            continue
        seeds = [r["header"] for r in native.values() if r["plan"] == row.const]
        queue = deque(sorted(seeds))
        seen = set(seeds)
        found = None
        for _ in range(len(native)):
            if not queue:
                break
            current = queue.popleft()
            if current in outside:
                found = native[current]["const"]
                break
            for target in sorted(links[current] - seen):
                seen.add(target)
                queue.append(target)
        # Les installations isolées (Salle Union, gabarits Safari) gardent leur lieu natif comme origine.
        row.origin = found or native[seeds[0]]["const"]
