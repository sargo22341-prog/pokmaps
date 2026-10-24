"""Pokémon fixes : seuls les acteurs natifs correspondant à une rencontre du lieu sont affichés."""

import csv
from pathlib import Path

from .maps_characters import ObjectRow
from .maps_layout import identifier
from .pokeapi import PokeApi
from .pret_hgss_maps import HgssMapRepo
from .references_hgss import HgssReferences
from .sources import DATA_DIR


def fixed_rows(
    root: Path, catalog: dict, maps: dict, offsets: dict, api: PokeApi, refs: HgssReferences
) -> list[ObjectRow]:
    from .maps_characters_hgss import project

    repo = HgssMapRepo(root, "heartgold")
    areas = _areas(api)
    slots = api.by_id("encounter_slots")
    methods = api.by_id("encounter_methods")
    species = {key.replace("-", "").upper(): key for key in refs.species.values()}
    candidates = []
    for encounter in api.table("encounters"):
        method = methods[int(slots[int(encounter["encounter_slot_id"])]["encounter_method_id"])]["identifier"]
        if encounter["version_id"] in {"15", "16"} and method in {"static", "pokeflute", "squirt-bottle"}:
            candidates.append(encounter)
    result = []
    for actor in catalog["actors"]:
        key = _species_key(actor["native"]["sprite"])
        pokemon = species.get(key)
        if pokemon is None:
            continue
        record = maps[actor["header"]]
        matches = [
            e
            for e in candidates
            if e["location_area_id"] in areas.get(record["const"], set())
            and refs.species[int(e["pokemon_id"])] == pokemon
        ]
        if not matches:
            continue
        point = project(repo, record, actor["native"])
        dx, dy = offsets[identifier(record["const"])]
        for version, level in sorted({(e["version_id"], int(e["min_level"])) for e in matches}):
            result.append(
                ObjectRow(
                    record["const"],
                    "pokemon",
                    point[0] + dx,
                    point[1] + dy,
                    None,
                    None,
                    pokemon,
                    level,
                    None,
                    version={"15": "heartgold", "16": "soulsilver"}[version],
                )
            )
    return result


def _species_key(sprite: str) -> str:
    # Les deux légendaires utilisent un acteur de scène, pas le sprite d'un accompagnateur.
    # zone_event/230_D40R0107.json et 311_D17R0110.json fixent leur position après l'apparition.
    scene_species = {"SPRITE_LUG_OBJ01": "LUGIA", "SPRITE_HOU_OBJ01": "HOOH"}
    return scene_species.get(sprite, sprite.removeprefix("SPRITE_FOLLOWER_MON_STATIC_").replace("_", ""))


def _areas(api: PokeApi) -> dict[str, set[str]]:
    locations = api.by_id("locations")
    keys = {
        locations[int(r["location_id"])]["identifier"] + ("/" + r["identifier"] if r["identifier"] else ""): r["id"]
        for r in api.table("location_areas")
    }
    result: dict[str, set[str]] = {}
    with (DATA_DIR / "hgss_area_bindings.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            result.setdefault(row["map"], set()).add(keys[row["area"]])
    return result
