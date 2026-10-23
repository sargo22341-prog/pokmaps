"""Lecture des parcours éditoriaux HGSS et résolution de leurs liens natifs."""

import csv

from .pret_gen4_source import read_json_list
from .sources import DATA_DIR


def guide_catalog(characters: dict, maps: list[dict]) -> list[dict]:
    entries = read_json_list(DATA_DIR / "hgss_guides.json")
    if not 1 <= len(entries) <= 128:
        raise ValueError("HGSS : nombre de guides hors limite")
    lookup = {row["const"]: row for row in maps}
    result = []
    for version in ("heartgold", "soulsilver"):
        for row in entries:
            if version not in row["versions"]:
                continue
            places = [lookup[name] for name in row["places"]]
            headers = {place["header"] for place in places}
            actors = [a for a in characters["actors"] if a["header"] in headers and a["link"] == "script_graph"]
            banks = {a["bank"] for a in actors}
            scripts = ["src/data/map_headers.h"] + [
                characters["scripts"][str(bank)]["source"] for bank in sorted(banks)
            ]
            result.append(
                row
                | dict(
                    version=version,
                    places=[dict(header=p["header"], name_fr=p["name_fr"]) for p in places],
                    actors=[dict(header=a["header"], event=a["event"], name_fr=a["name_fr"]) for a in actors],
                    items=[
                        dict(
                            id=o["id"],
                            values=o["values"],
                            command=o["command"],
                            quantity_rule=o.get("quantity_rule"),
                            source=o["source"],
                            instruction=o["instruction"],
                            conditions_fr=o["conditions_fr"],
                            native_version=o["version"],
                        )
                        for o in characters["service_steps"]
                        if o["bank"] in banks
                        and o["command"] in ("GiveItem", "GiveItemNoCheck", "offer_item")
                        and o["version"] in ("externe", {"heartgold": 7, "soulsilver": 8}[version])
                    ],
                    sources=scripts,
                )
            )
    return result


def map_entries() -> list[dict]:
    with (DATA_DIR / "hgss_maps.csv").open(encoding="utf-8", newline="") as handle:
        return [dict(row, header=int(row["header"])) for row in csv.DictReader(handle) if row["scope"] != "excluded"]


def weekly_calendar(characters: dict) -> list[dict]:
    rows = read_json_list(DATA_DIR / "hgss_calendar.json")
    if not 1 <= len(rows) <= 64:
        raise ValueError("HGSS : nombre de rendez-vous hors limite")
    maps = {row["const"]: row for row in map_entries()}
    result = []
    for row in rows:
        headers = {maps[name]["header"] for name in row["places"]}
        banks = {a["bank"] for a in characters["actors"] if a["header"] in headers}
        result.append(
            row
            | dict(headers=sorted(headers), sources=[characters["scripts"][str(b)]["source"] for b in sorted(banks)])
        )
    return result


def validate_guides(rows: list[dict]) -> None:
    keys = set()
    for row in rows:
        key = row["version"], row["id"]
        if key in keys or not row["title_fr"].strip() or not row["text_fr"].strip():
            raise ValueError(f"HGSS : guide dupliqué ou vide : {key}")
        keys.add(key)
        if not row["places"] or not row["sources"]:
            raise ValueError(f"HGSS : guide sans preuve ou lieu : {key}")
        if row["category"] not in ("johto", "kanto", "postgame", "quest", "activity"):
            raise ValueError(f"HGSS : catégorie de guide inconnue : {key}")
    for version in ("heartgold", "soulsilver"):
        selected = [r for r in rows if r["version"] == version]
        for category, minimum in (("johto", 18), ("kanto", 10), ("postgame", 3), ("quest", 5)):
            if sum(r["category"] == category for r in selected) < minimum:
                raise ValueError(f"HGSS : parcours incomplet : {version}/{category}")
        ids = {r["id"] for r in selected}
        for row in selected:
            if not set(row["requires"]) <= ids:
                raise ValueError(f"HGSS : prérequis de guide inconnu : {row['id']}")
        completed: set[str] = set()
        for row in selected:
            if not set(row["requires"]) <= completed:
                raise ValueError(f"HGSS : étapes désordonnées ou cycliques : {row['id']}")
            completed.add(row["id"])
