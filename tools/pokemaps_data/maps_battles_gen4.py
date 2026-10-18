"""Un personnage par combat de scénario DS, avec toutes ses équipes et ses choix de départ."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

from .maps_characters import ObjectRow
from .maps_characters_gen4 import _attach_team, _item, _party
from .pret_gen4_flow import reachable
from .pret_gen4_offer_sites import offer_sites
from .pret_models import VariantKind
from .sources import DATA_DIR

if TYPE_CHECKING:
    from .builder import DatabaseBuilder
    from .maps_export_gen4 import Gen4MapProjection
    from .pret_gen4_battles import ScriptBattle
    from .pret_gen4_offer_sites import OfferSite
    from .pret_gen4_trainers import Gen4Trainer
    from .preview_characters_gen4 import CharacterCatalog


def merge_story_actors(rows: list[ObjectRow]) -> list[ObjectRow]:
    named = {"99", "140", "148", *(str(number) for number in (120, 121, 122, 123, *range(126, 140), *range(141, 146)))}
    retained: dict[tuple[str, str], ObjectRow] = {}
    result = []
    for row in rows:
        if row.sprite not in named:
            result.append(row)
            continue
        key = (row.map_const, row.sprite)
        if key in retained:
            first = retained[key]
            if (first.party, first.variants, first.rematches) != (row.party, row.variants, row.rematches):
                raise ValueError(f"{row.map_const}:{row.sprite} : poses avec des combats distincts à réunir")
            first.offers = list(dict.fromkeys([*first.offers, *row.offers]))
        else:
            retained[key] = row
            result.append(row)
    return result


def attach_script_battles(
    builder: DatabaseBuilder,
    catalog: CharacterCatalog,
    projection: Gen4MapProjection,
    rows: list[ObjectRow],
    source: Path,
) -> None:
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    graphics_by_class = _battle_sprites()
    groups: dict[tuple[str, str, str, int], list[tuple[int, int | None, ScriptBattle]]] = defaultdict(list)
    for battle in catalog.script_battles:
        for const in catalog.script_headers[battle.script_file]:
            for variant in battle.variants:
                for slot, number in enumerate(variant.opponents):
                    trainer = trainers[number]
                    groups[const, trainer.trainer_class, trainer.name, slot].append(
                        (number, variant.player_starter, battle)
                    )
    if missing := {key[1].removeprefix("TRAINER_CLASS_") for key in groups} - graphics_by_class.keys():
        raise ValueError(f"trainer_sprites_gen4.csv : classes sans apparence : {sorted(missing)}")
    for (const, trainer_class, _, _slot), variants in groups.items():
        graphics = graphics_by_class[trainer_class.removeprefix("TRAINER_CLASS_")]
        if not (source / "sprites" / f"{graphics}.webp").is_file():
            raise ValueError(f"trainer_sprites_gen4.csv : sprite absent de {source.name} : {trainer_class}:{graphics}")
        candidates = [
            row for row in rows if row.map_const == const and row.sprite == graphics and row.kind != "trainer"
        ]
        row = _actor(catalog, projection, const, variants[0][2], candidates, rows)
        row.sprite = graphics
        _attach_team(builder, catalog, row, trainers[variants[0][0]])
        _teams(builder, row, trainers, list(dict.fromkeys((number, starter) for number, starter, _ in variants)))


def _actor(
    catalog: CharacterCatalog,
    projection: Gen4MapProjection,
    const: str,
    battle: ScriptBattle,
    candidates: list[ObjectRow],
    rows: list[ObjectRow],
) -> ObjectRow:
    origins = _origins(projection, const, battle)
    keys = {
        actor.key
        for actor in catalog.actors.actors
        if actor.header == const and any(site.kind == "object" and site.event == actor.event for site in origins)
    }
    matched = [row for row in candidates if row.key in keys]
    # Les protagonistes ont une apparence propre ; les figurants d'une même classe restent distincts.
    if not matched:
        matched = [
            row for row in candidates if row.sprite and int(row.sprite) in {120, 121, 122, 123, *range(126, 149)}
        ]
    if not matched and candidates:
        origin = origins[0] if origins else None
        point = projection.point(const, origin.x, origin.z) if origin else (candidates[0].x, candidates[0].y)
        matched = [min(candidates, key=lambda row: (row.x - point[0]) ** 2 + (row.y - point[1]) ** 2)]
    if matched:
        row = matched[0]
        for duplicate in matched[1:]:
            row.offers = list(dict.fromkeys([*row.offers, *duplicate.offers]))
            rows.remove(duplicate)
        return row
    region = projection.maps.by_const[const]
    point = (region.x + region.width // 2, region.y + region.height // 2)
    cell = None
    if origins:
        site = origins[0]
        if site.x is not None and site.z is not None:
            cell = (site.x, site.z)
            point = projection.point(const, *cell)
    row = ObjectRow(const, "trainer", *point, None, None, None, None, None, source_cell=cell)
    rows.append(row)
    return row


def _origins(projection: Gen4MapProjection, const: str, battle: ScriptBattle) -> list[OfferSite]:
    repo = projection.maps.repo
    header = projection.maps.headers[const]
    flow = repo.flows[battle.script_file]
    targets = {step.key for step in flow.steps.values() if step.source == battle.step}
    sites, _ = offer_sites(repo, header)
    return [
        site
        for site in sites
        if site.script_file == battle.script_file
        and site.x is not None
        and site.z is not None
        and targets & reachable(flow, flow.entries[site.entry])
    ]


def _teams(
    builder: DatabaseBuilder, row: ObjectRow, trainers: dict[int, Gen4Trainer], variants: list[tuple[int, int | None]]
) -> None:
    numbers = list(dict.fromkeys(number for number, _ in variants))
    # Le choix du partenaire ne crée pas une variante de l'équipe adverse quand celle-ci est identique.
    dependent = len(numbers) > 1 and all(starter is not None for _, starter in variants)
    selected = variants if dependent else [(number, None) for number in numbers]
    # Les scripts testent parfois la revanche la plus forte avant le combat initial.
    selected = sorted(
        selected,
        key=lambda pair: (
            pair[1] or 0,
            max(mon.level for mon in trainers[pair[0]].party),
            pair[0],
        ),
    )
    row.party, row.rematches, row.variants = [], [], []
    row.variant_rematches = {}
    if dependent:
        row.variants = [
            (VariantKind.PLAYER_STARTER, builder.species[starter]["identifier"], _party(trainers[number]))
            for number, starter in selected
        ]
        occurrences: dict[int | None, int] = {}
        for team, (_, starter) in enumerate(selected, start=1):
            rematch = occurrences.get(starter, 0)
            if rematch:
                row.variant_rematches[team] = rematch
            occurrences[starter] = rematch + 1
    else:
        row.party = _party(trainers[selected[0][0]])
        row.rematches = [_party(trainers[number]) for number, _ in selected[1:]]
    row.held_items = {
        (team, slot): _item(builder, mon.item)
        for team, (number, _) in enumerate(selected, start=1)
        for slot, mon in enumerate(trainers[number].party, start=1)
        if mon.item
    }


def _battle_sprites() -> dict[str, str]:
    result = {}
    with (DATA_DIR / "trainer_sprites_gen4.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["trainer_class", "graphics"]:
            raise ValueError("trainer_sprites_gen4.csv : colonnes invalides")
        for row in reader:
            key, graphics = row["trainer_class"], row["graphics"]
            if not key or key in result or not graphics.isdecimal():
                raise ValueError(f"trainer_sprites_gen4.csv : classe ou apparence invalide : {row}")
            result[key] = graphics
    return result
