"""Personnages GBA, Pokémon fixes et catalogue des données de scénario."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .character_curation_gen3 import character_key, read_gen3_curation
from .hoenn_character_state import display_event, display_result
from .hoenn_scene_actors import attach_scenes, validate_scene_actors
from .hoenn_team_battles import team_battle
from .hoenn_team_graphics import apply_team_graphics, team_graphics
from .maps_characters import ObjectRow
from .maps_characters_data import read_character_names
from .maps_facilities_gen3 import facility_rows
from .maps_items_gen3 import _identifier, item_rows
from .maps_layout_gen3 import Gen3GameMaps
from .maps_offers_gen3 import CATALOG_ONLY_KINDS, mark_alternative_conditions, offer_row, repo_name
from .maps_scenes_gen3 import scene_rows
from .maps_trainers_gen3 import trainer_rows
from .pokeapi import PokeApi
from .pret_gen3_conditions import ScriptRequirement
from .pret_gen3_fixed import fixed_encounters
from .pret_gen3_maps import Gen3Event, Gen3Map
from .pret_gen3_offers import ScriptOffers
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
        if not maps.repo.remake:
            validate_scene_actors(maps.repo, version)
        berries = initial_berries(maps.repo, version) if maps.game.map_family == "ruby-sapphire-emerald" else {}
        for const in sorted(maps.placements, key=lambda key: maps.maps[key].number):
            current = maps.maps[const]
            graphics = team_graphics(current, reader.scripts) if maps.repo.ruby else {}
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
                result = _object_result(maps, current, index, event, graphics, version, story)
                displayed = display_event(current, event) if not maps.repo.remake else event
                if displayed is not None and not maps.repo.remake:
                    result = display_result(current, displayed, result, reader)
                if result.unresolved:
                    raise ValueError(f"{version}:{key} : offres non résolues : {result.unresolved}")
                catalog.append(_catalog_row(version, current.const, key, event, result))
                _mark_offer_conditions(maps, result, version, story)
                offers = _display_offers(maps, event, result, version, api, story, berries)
                if displayed is None:
                    continue
                event = displayed
                event = apply_team_graphics(event, graphics)
                # Les journaux du Memorydex restent au catalogue, sans acteur ni service à afficher sur la carte.
                if event.value("movement_type") == "MOVEMENT_TYPE_INVISIBLE" and not result.trainers and not offers:
                    continue
                rows.extend(_actor_rows(maps, current, event, version, result.trainers, offers))
        rows = _replace_fixed_actors(rows, maps, version)
        rows.extend(facility_rows(maps, version, api, story))
    _write_catalog(maps, story, output, catalog, [asdict(item) for item in items])
    return rows


def _object_result(
    maps: Gen3GameMaps,
    current: Gen3Map,
    index: int,
    event: Gen3Event,
    graphics: dict[str, str],
    version: str,
    story: StoryEvents,
) -> ScriptOffers:
    reader = maps.repo.offers[version]
    result = reader.read_curated_object(current.label, event, index, maps.game.map_family)
    if maps.repo.remake:
        return result
    result = attach_scenes(current, index, event, result, reader, version)
    # Valider aussi les chemins des scènes dont les offres appartiennent ensuite à un autre acteur.
    _mark_offer_conditions(maps, result, version, story)
    return team_battle(
        current, index, apply_team_graphics(event, graphics), result, reader, maps.repo.trainers[version]
    )


def _mark_offer_conditions(maps: Gen3GameMaps, result: ScriptOffers, version: str, story: StoryEvents) -> None:
    for offer in result.offers:
        mark_alternative_conditions(offer, maps.repo, version, story)


def _display_offers(
    maps: Gen3GameMaps,
    event: Gen3Event,
    result: ScriptOffers,
    version: str,
    api: PokeApi,
    story: StoryEvents,
    berries: dict[int, str],
) -> list[NpcOffer]:
    if event.value("movement_type") == "MOVEMENT_TYPE_BERRY_TREE_GROWTH":
        return _berry_offers(event, berries, maps.repo.offers[version].scripts.constants, version)
    return [
        offer_row(offer, maps.repo, version, api, story)
        for offer in result.offers
        if offer.kind not in CATALOG_ONLY_KINDS
    ]


def _write_catalog(
    maps: Gen3GameMaps,
    story: StoryEvents,
    output: Path,
    catalog: list[dict[str, object]],
    items: list[dict[str, object]],
) -> None:
    payload = {
        "schema": 1,
        "commit": PRET_COMMITS[repo_name(maps.repo)],
        "characters": catalog,
        "items": items,
        "scenes": scene_rows(maps.repo, story),
    }
    (output / "characters.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=_json_value) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
    actor = ObjectRow(
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
    return trainer_rows(maps, version, trainers, actor) if trainers else [actor]


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


def _replace_fixed_actors(rows: list[ObjectRow], maps: Gen3GameMaps, version: str) -> list[ObjectRow]:
    fixed = _fixed_rows(maps, version)
    positions = {(row.map_const, row.x, row.y) for row in fixed}
    retained = [
        row
        for row in rows
        if row.version != version or row.kind != "npc" or row.offers or (row.map_const, row.x, row.y) not in positions
    ]
    return retained + fixed
