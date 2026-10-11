"""Personnages GBA, Pokémon fixes et catalogue des données de scénario."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .character_curation_gen3 import character_key, read_gen3_curation
from .maps_characters import ObjectRow
from .maps_characters_data import read_character_names
from .maps_facilities_gen3 import facility_rows
from .maps_items_gen3 import _identifier, item_rows
from .maps_layout_gen3 import Gen3GameMaps
from .maps_offers_gen3 import CATALOG_ONLY_KINDS, mark_alternative_conditions, offer_row, repo_name
from .maps_scenes_gen3 import scene_rows
from .pokeapi import PokeApi
from .pret_gen3_conditions import ScriptRequirement
from .pret_gen3_fixed import fixed_encounters
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import ScriptOffers
from .pret_gen3_trainers import Gen3TrainerPokemon
from .pret_hoenn_berries import initial_berries
from .pret_identifiers import species_identifier
from .pret_models import NpcOffer
from .sources import PRET_COMMITS
from .story_events import StoryEvents


def character_rows(maps: Gen3GameMaps, api: PokeApi, story: StoryEvents, output: Path) -> list[ObjectRow]:
    rows, items = item_rows(maps)
    curation = read_gen3_curation()
    catalog: list[dict[str, object]] = []
    for version, _ in maps.game.pret_versions:
        reader = maps.repo.offers[version]
        berries = initial_berries(maps.repo, version) if maps.game.map_family == "ruby-sapphire-emerald" else {}
        for const in sorted(maps.placements, key=lambda key: maps.maps[key].number):
            current = maps.maps[const]
            for index, event in enumerate(current.objects, 1):
                key = character_key(current.label, event, index)
                if event.kind == "clone" or curation.is_duplicate(maps.game.map_family, key):
                    continue
                if any(
                    item.version == version and item.map_const == const and item.script == str(event.value("script"))
                    for item in items
                ):
                    continue
                # Les figurants de scènes attendent parfois hors du layout ; events.json les conserve.
                if not (0 <= event.x < current.width and 0 <= event.y < current.height):
                    continue
                result = reader.read_curated_object(current.label, event, index, maps.game.map_family)
                if result.unresolved:
                    raise ValueError(f"{version}:{key} : offres non résolues : {result.unresolved}")
                catalog.append(_catalog_row(version, current.const, key, event, result))
                for offer in result.offers:
                    mark_alternative_conditions(offer, maps.repo, version, story)
                offers = (
                    [
                        offer_row(offer, maps.repo, version, api, story)
                        for offer in result.offers
                        if offer.kind not in CATALOG_ONLY_KINDS
                    ]
                    if event.value("movement_type") != "MOVEMENT_TYPE_BERRY_TREE_GROWTH"
                    else _berry_offers(event, berries, reader.scripts.constants, version)
                )
                # Les journaux du Memorydex restent au catalogue, sans acteur ni service à afficher sur la carte.
                if event.value("movement_type") == "MOVEMENT_TYPE_INVISIBLE" and not result.trainers and not offers:
                    continue
                rows.extend(_actor_rows(maps, current, event, version, result.trainers, offers))
        rows = _replace_fixed_actors(rows, maps, version)
        rows.extend(facility_rows(maps, version, api, story))
    payload = {
        "schema": 1,
        "commit": PRET_COMMITS[repo_name(maps.repo)],
        "characters": catalog,
        "items": [asdict(item) for item in items],
        "scenes": scene_rows(maps.repo, story),
    }
    (output / "characters.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_value) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return rows


def _berry_offers(event: Gen3Event, berries: dict[int, str], constants: dict[str, int], version: str) -> list[NpcOffer]:
    value = str(event.value("trainer_sight_or_berry_tree_id"))
    number = int(value) if value.isdecimal() else constants[value]
    item = berries.get(number)
    return [NpcOffer("fruit_tree", item=_identifier(item, constants), version=version)] if item else []


def _json_value(value: object) -> object:
    if isinstance(value, ScriptRequirement):
        return asdict(value)
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(f"Valeur de catalogue non sérialisable : {value}")


def _catalog_row(version: str, const: str, key: str, event: Gen3Event, result: ScriptOffers) -> dict[str, object]:
    return {"version": version, "map_const": const, "key": key, "event": asdict(event), "result": asdict(result)}


def _actor_rows(
    maps: Gen3GameMaps,
    current: Gen3Map,
    event: Gen3Event,
    version: str,
    trainers: tuple[str, ...],
    offers: list[NpcOffer],
) -> list[ObjectRow]:
    names = read_character_names()
    raw_sprite = str(event.value("graphics_id"))
    dynamic = raw_sprite.startswith("OBJ_EVENT_GFX_VAR_")
    invisible = event.value("movement_type") == "MOVEMENT_TYPE_INVISIBLE"
    sprite = None if dynamic or invisible else raw_sprite.lower().replace("_", "-")
    script = str(event.value("script"))
    default = names.character("DYNAMIC_CHARACTER" if dynamic else raw_sprite)
    name = names.by_text.get(script, default)
    appearance = names.npc_kind("DYNAMIC_CHARACTER" if dynamic else raw_sprite)
    point = maps.point(current.const, event.x, event.y)
    if not trainers:
        return [
            ObjectRow(
                current.const,
                "npc",
                *point,
                sprite,
                None,
                None,
                None,
                None,
                key=script,
                offers=offers,
                version=version,
                name_fr=name,
                appearance=appearance,
            )
        ]
    rows = []
    for trainer_id in trainers:
        trainer = maps.repo.trainers[version][trainer_id]
        party = _party_rows(trainer.party)
        rows.append(
            ObjectRow(
                current.const,
                "trainer",
                *point,
                sprite,
                None,
                None,
                None,
                trainer.trainer_class,
                key=script,
                party=party,
                offers=offers,
                version=version,
                name_fr=names.trainer(trainer.trainer_class),
            )
        )
    return rows


def _fixed_rows(maps: Gen3GameMaps, version: str) -> list[ObjectRow]:
    rows = []
    by_label = {current.label: const for const, current in maps.maps.items()}
    for fixed in fixed_encounters(maps.repo, version):
        const = by_label[str(fixed["map"])]
        if const not in maps.placements:
            continue
        species = species_identifier(str(fixed["pokemon"]).removeprefix("SPECIES_"))
        row = ObjectRow(
            const,
            "pokemon",
            *maps.point(const, int(fixed["x"]), int(fixed["y"])),
            None,
            None,
            species,
            int(fixed["level"]),
            None,
            version=version,
        )
        if row not in rows:
            rows.append(row)
    return rows


def _party_rows(party: tuple[Gen3TrainerPokemon, ...]) -> list[tuple[str, int, tuple[str, ...]]]:
    return [
        (
            species_identifier(mon.species.removeprefix("SPECIES_")),
            mon.level,
            tuple(move.removeprefix("MOVE_").lower().replace("_", "-") for move in mon.moves),
        )
        for mon in party
    ]


def _replace_fixed_actors(rows: list[ObjectRow], maps: Gen3GameMaps, version: str) -> list[ObjectRow]:
    fixed = _fixed_rows(maps, version)
    positions = {(row.map_const, row.x, row.y) for row in fixed}
    retained = [
        row
        for row in rows
        if row.version != version or row.kind != "npc" or row.offers or (row.map_const, row.x, row.y) not in positions
    ]
    return retained + fixed
