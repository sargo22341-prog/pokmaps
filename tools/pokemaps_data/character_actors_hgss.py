"""Liens natifs acteur/script/lieu HGSS et alertes de relecture des placements."""

import re
from dataclasses import asdict
from pathlib import Path

from .catalog_maps_hgss import read_catalog
from .pret_gen4_source import c_defines, read_json
from .pret_hgss_maps import HgssMapRepo
from .pret_hgss_scripts import Script, reachable
from .pret_hgss_services import service_steps


def actor_catalog(
    root: Path,
    scripts: dict[int, Script],
    battles: list[dict],
    items: dict[str, dict],
    offers: list[dict] | None = None,
) -> dict:
    repo = HgssMapRepo(root, "heartgold")
    trainers = c_defines(root / "include/constants/trainers.h", "TRAINER_")
    entries = read_catalog(repo)
    services = service_steps(scripts) if offers is None else offers
    actors, objects, scenes = [], [], []
    for place in entries:
        if place.scope == "excluded":
            continue
        header = repo.headers[place.header]
        events = repo.events(header)
        raw = read_json(root / events.source)
        bank_match = re.search(r"scr_seq_(\d+)", dict(header.fields)["scriptsBank"])
        if bank_match is None:
            raise ValueError(f"HGSS : banque de scripts inconnue : {header.constant}")
        bank = int(bank_match[1])
        for index, actor in enumerate(events.actors):
            record = dict(
                header=header.index,
                place_fr=place.name_fr,
                event=index,
                source=events.source,
                native=asdict(actor),
                event_fields=raw["objects"][index],
                bank=bank,
                near_warp=any(abs(actor.x - w.x) <= 1 and abs(actor.z - w.z) <= 1 for w in events.warps),
            )
            record.update(_links(actor.script, bank, scripts, battles, trainers))
            visited = reachable(scripts[bank], record["script_entry"]) if record["script_entry"] else set()
            record["service_steps"] = [
                s["instruction"] for s in services if s["bank"] == bank and s["instruction"] in visited
            ]
            record["useful"] = bool(
                record["trainers"]
                or record["service_steps"]
                or actor.script.startswith(
                    ("std_apricorn_tree", "std_daycare_", "std_nurse_joy", "std_frontier_move_tutor_")
                )
            )
            if actor.script in items:
                objects.append(record | dict(item=items[actor.script]))
            else:
                actors.append(record)
        objects.extend(_background_items(raw, header.index, place.name_fr, events.source, items))
        scenes.extend(
            dict(header=header.index, source=events.source, event=index, native=event, bank=bank)
            for index, event in enumerate(raw.get("coords", []))
        )
    return dict(actors=actors, field_items=objects, scenes=scenes)


def _links(
    reference: str, bank: int, scripts: dict[int, Script], battles: list[dict], trainers: dict[str, int]
) -> dict:
    standard = re.fullmatch(r"std_trainer(?:_2)?\((TRAINER_\w+)\)", reference)
    if standard:
        return dict(trainers=[trainers[standard[1]]], battles=[], script_entry=None, link="standard_trainer")
    local = re.fullmatch(r"_EV_(\w+)\s*\+\s*1", reference)
    if local:
        entry = local[1]
        visited = reachable(scripts[bank], entry)
        sites = [b for b in battles if b["bank"] == bank and b["instruction"] in visited]
        return dict(
            trainers=sorted({t for b in sites for t in b["trainers"]}),
            battles=[b["instruction"] for b in sites],
            script_entry=entry,
            link="script_graph",
        )
    return dict(trainers=[], battles=[], script_entry=None, link="standard_or_no_script")


def _background_items(raw: dict, header: int, place: str, source: str, items: dict) -> list[dict]:
    return [
        dict(header=header, place_fr=place, event=index, source=source, native=bg, item=items[bg["scriptId"]])
        for index, bg in enumerate(raw.get("bgs", []))
        if bg["scriptId"] in items
    ]
