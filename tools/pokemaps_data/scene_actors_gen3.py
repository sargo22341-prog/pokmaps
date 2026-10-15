"""Rattachement éditorial des scènes GBA à leurs véritables acteurs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from functools import cache

from .pret_gen3 import Gen3PretRepo
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import Gen3Offers, ScriptOffers
from .sources import DATA_DIR

_VERSIONS = frozenset({"ruby", "sapphire", "emerald", "firered", "leafgreen"})


@dataclass(frozen=True)
class _SceneActor:
    version: str
    map_label: str
    index: int
    script: str
    # Combats (TRAINER_*) et dons (ITEM_*) de la scène qui reviennent à cet acteur ; vide : toute la scène.
    only: frozenset[str]
    condition: str


@cache
def _scene_actors() -> tuple[_SceneActor, ...]:
    with (DATA_DIR / "scene_actors_gen3.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["version", "map", "index", "script", "only", "condition"]:
            raise ValueError("scene_actors_gen3.csv : colonnes invalides")
        rows = tuple(
            _SceneActor(
                r["version"],
                r["map"],
                int(r["index"]),
                r["script"],
                frozenset(filter(None, r["only"].split("|"))),
                r["condition"],
            )
            for r in reader
        )
    if len({(r.version, r.map_label, r.index, r.script) for r in rows}) != len(rows):
        raise ValueError("scene_actors_gen3.csv : scène répétée")
    if any(r.version not in _VERSIONS or r.index < 1 or not r.script for r in rows):
        raise ValueError("scene_actors_gen3.csv : acteur ou version invalide")
    if any(not value.startswith(("TRAINER_", "ITEM_")) for r in rows for value in r.only):
        raise ValueError("scene_actors_gen3.csv : seuls des combats et des objets peuvent être retenus")
    return rows


def validate_scene_actors(repo: Gen3PretRepo, version: str) -> None:
    maps = {current.label: current for current in repo.maps.values()}
    for row in _scene_actors():
        if row.version != version:
            continue
        current = maps.get(row.map_label)
        if current is None or not 1 <= row.index <= len(current.objects):
            raise ValueError(f"scene_actors_gen3.csv : acteur absent : {row}")
        if row.script not in repo.offers[version].scripts.blocks:
            raise ValueError(f"scene_actors_gen3.csv : script absent : {row}")
        scene = repo.offers[version].read(row.script)
        found = set(scene.trainers) | {offer.item for offer in scene.offers if offer.item}
        if missing := row.only - found:
            raise ValueError(f"scene_actors_gen3.csv : {sorted(missing)} absent de la scène : {row}")


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
        trainers.extend(trainer for trainer in scene.trainers if not row.only or trainer in row.only)
        offers.extend(
            replace(offer, conditions=tuple(dict.fromkeys((*offer.conditions, row.condition))))
            if row.condition
            else offer
            for offer in scene.offers
            if not row.only or offer.item in row.only
        )
    if current.label == "Route104" and "RIVAL" in str(event.value("flag")):
        trainers = []  # Le combat facultatif de Mérouville utilise aussi cet acteur de transition.
    if current.label == "MossdeepCity_Gym" and event.value("graphics_id") == "OBJ_EVENT_GFX_LIZA":
        trainers = []  # Une seule fiche pour l'équipe commune du combat double.
        offers = []
    return replace(result, trainers=tuple(sorted(set(trainers))), offers=tuple(dict.fromkeys(offers)))
