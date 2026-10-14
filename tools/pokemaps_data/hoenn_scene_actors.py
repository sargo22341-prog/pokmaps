"""Rattachement éditorial des scènes Hoenn à leurs véritables acteurs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from functools import cache

from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import Gen3Offers, ScriptOffers
from .sources import DATA_DIR


@dataclass(frozen=True)
class _SceneActor:
    version: str
    map_label: str
    index: int
    script: str
    condition: str


@cache
def _scene_actors() -> tuple[_SceneActor, ...]:
    with (DATA_DIR / "hoenn_scene_actors.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["version", "map", "index", "script", "condition"]:
            raise ValueError("hoenn_scene_actors.csv : colonnes invalides")
        rows = tuple(_SceneActor(r["version"], r["map"], int(r["index"]), r["script"], r["condition"]) for r in reader)
    if len({(r.version, r.map_label, r.index, r.script) for r in rows}) != len(rows):
        raise ValueError("hoenn_scene_actors.csv : scène répétée")
    if any(r.version not in {"ruby", "sapphire", "emerald"} or r.index < 1 or not r.script for r in rows):
        raise ValueError("hoenn_scene_actors.csv : acteur ou version invalide")
    return rows


def validate_scene_actors(repo: Gen3PretRepo, version: str) -> None:
    maps = {current.label: current for current in repo.maps.values()}
    for row in _scene_actors():
        if row.version != version:
            continue
        current = maps.get(row.map_label)
        if current is None or not 1 <= row.index <= len(current.objects):
            raise ValueError(f"hoenn_scene_actors.csv : acteur absent : {row}")
        if row.script not in repo.offers[version].scripts.blocks:
            raise ValueError(f"hoenn_scene_actors.csv : script absent : {row}")


def attach_scenes(
    current: Gen3Map,
    index: int,
    event: Gen3Event,
    result: ScriptOffers,
    reader: Gen3Offers,
    version: str,
) -> ScriptOffers:
    offers, trainers = list(result.offers), list(result.trainers)
    for row in _scene_actors():
        if (row.version, row.map_label, row.index) != (version, current.label, index):
            continue
        if current.objects[index - 1] != event:
            raise ValueError(f"{current.label}:{index} : acteur de scène déplacé")
        scene = reader.read(row.script)
        if not scene.offers and not scene.trainers:
            raise ValueError(f"{version}:{row.script} : scène sans don ni combat")
        trainers.extend(scene.trainers)
        offers.extend(
            replace(offer, conditions=tuple(dict.fromkeys((*offer.conditions, row.condition))))
            if row.condition
            else offer
            for offer in scene.offers
        )
    if current.label == "Route104" and "RIVAL" in str(event.value("flag")):
        trainers = []  # Le combat facultatif de Mérouville utilise aussi cet acteur de transition.
    if current.label == "MossdeepCity_Gym" and event.value("graphics_id") == "OBJ_EVENT_GFX_LIZA":
        trainers = []  # Une seule fiche pour l'équipe commune du combat double.
        offers = []
    return replace(result, trainers=tuple(sorted(set(trainers))), offers=tuple(dict.fromkeys(offers)))
