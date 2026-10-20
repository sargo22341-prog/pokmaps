"""Audit des omissions entre les sources DS épinglées et la base distribuée, lieu par lieu."""

import sqlite3
from collections import defaultdict
from pathlib import Path

import pytest

from pokemaps_data.builder import DatabaseBuilder
from pokemaps_data.games import GEN4_GAMES, Game
from pokemaps_data.maps_data_gen4 import Gen4WildMaps
from pokemaps_data.maps_export_gen4 import Gen4MapProjection
from pokemaps_data.maps_layout import identifier
from pokemaps_data.maps_layout_gen4 import selected_headers
from pokemaps_data.maps_offers_gen4 import actor_offers
from pokemaps_data.maps_passages_gen4 import warps
from pokemaps_data.pret_gen4 import Gen4PretRepo
from pokemaps_data.pret_identifiers import species_identifier
from pokemaps_data.pret_items_gen4 import ds_item_id
from pokemaps_data.preview_characters_gen4 import CharacterCatalog, character_catalog
from pokemaps_data.preview_encounters_gen4 import complete_preview_encounters
from pokemaps_data.sources import pret_dir
from pokemaps_data.validate import CHECKS

_CACHE = Path(__file__).resolve().parents[1] / ".cache"


@pytest.fixture(scope="module", params=GEN4_GAMES, ids=lambda game: game.version_group)
def catalog(request: pytest.FixtureRequest, source_cache_ready: None) -> CharacterCatalog:
    game: Game = request.param
    return character_catalog(Gen4PretRepo(pret_dir(_CACHE, game.pret_repo), game.pret_versions), game)


@pytest.fixture(scope="module")
def projection(catalog: CharacterCatalog, gen4_builder: DatabaseBuilder, assets: Path) -> Gen4MapProjection:
    game = next(game for game in GEN4_GAMES if game.version_group == catalog.version_group)
    repo = gen4_builder.gen4_repo(game, "l'audit des objets")
    context = gen4_builder.encounters.gen4_contexts[game.version_group]
    maps = Gen4WildMaps(assets / "maps" / game.version_group, repo, game, context)
    # La projection utilise les matrices natives ; les translations des plans sont ajoutées ensuite.
    maps.parents.update({const: native for const, (native, _) in maps.assembly_coordinates.items()})
    return Gen4MapProjection(maps)


def _places(db: sqlite3.Connection, catalog: CharacterCatalog) -> dict[str, int]:
    rows = db.execute(
        """SELECT m.id, m.identifier, coalesce(m.parent_map_id, m.id) FROM map m
           JOIN version_group v ON v.id = m.version_group_id WHERE v.identifier = ?""",
        (catalog.version_group,),
    ).fetchall()
    places = {name: parent for _, name, parent in rows}
    return {const: places[identifier(const)] for const in catalog.headers.values()}


def test_selected_headers_are_all_distributed_and_excluded_copies_stay_absent(
    db: sqlite3.Connection, catalog: CharacterCatalog, gen4_builder: DatabaseBuilder
) -> None:
    game = next(game for game in GEN4_GAMES if game.version_group == catalog.version_group)
    repo = gen4_builder.gen4_repo(game, "l'audit des lieux")
    actual = {
        row[0]
        for row in db.execute(
            """SELECT m.identifier FROM map m JOIN version_group v ON v.id = m.version_group_id
           WHERE v.identifier = ?""",
            (catalog.version_group,),
        )
    }
    raw = {identifier(header.constant) for header in repo.headers.values()}
    expected = {identifier(const) for const in catalog.headers.values()}
    assert raw & actual == expected


def test_only_known_abandoned_doors_lead_to_excluded_copies(
    catalog: CharacterCatalog, gen4_builder: DatabaseBuilder
) -> None:
    game = next(game for game in GEN4_GAMES if game.version_group == catalog.version_group)
    repo = gen4_builder.gen4_repo(game, "l'audit des portes abandonnées")
    # Vestiges des maisons de Féli-Cité et Rivamar ; Platine garde aussi les anciens étages et Arènes DP.
    expected = {(3, 31), (3, 32), (150, 161), (150, 162)}
    if repo.platinum:
        expected |= {(20, 21), (25, 26), (51, 52), (55, 56), (62, 63), (67, 68), (78, 79), (91, 92), (91, 93), (91, 94)}
    actual = {(row.source, row.target) for row in warps(repo, selected_headers(repo)) if row.kind == "unused"}
    assert actual == expected


def test_every_event_and_story_opponent_keeps_all_teams(
    db: sqlite3.Connection, catalog: CharacterCatalog, gen4_builder: DatabaseBuilder
) -> None:
    places = _places(db, catalog)
    trainers = {trainer.id: trainer for trainer in catalog.trainers}
    species = dict(db.execute("SELECT identifier, id FROM pokemon"))
    rows = db.execute(
        """SELECT coalesce(m.parent_map_id, m.id), o.id, t.team, t.pokemon_id, t.level, t.held_item_id,
                  t.move1_id, t.move2_id, t.move3_id, t.move4_id
           FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN trainer_pokemon t ON t.map_object_id = o.id ORDER BY o.id, t.team, t.slot"""
    )
    parties: dict[tuple[int, int, int], list[tuple]] = defaultdict(list)
    for place, actor, team, mon, level, item, *attacks in rows:
        parties[place, actor, team].append((mon, level, item, tuple(move for move in attacks if move is not None)))
    displayed = {(place, tuple(party)) for (place, _, _), party in parties.items()}
    expected = {(catalog.headers[event.header], event.trainer) for event in catalog.event_trainers}
    expected |= {
        (const, number)
        for battle in catalog.script_battles
        for const in catalog.script_headers[battle.script_file]
        for variant in battle.variants
        for number in variant.opponents
    }
    rematches = {series.base: series.teams for series in catalog.vs_seeker.series}
    expected |= {(const, team) for const, number in list(expected) for team in rematches.get(number, ()) if team}
    missing = []
    for const, number in sorted(expected):
        party = tuple(
            (
                species[species_identifier(mon.species.removeprefix("SPECIES_"))],
                mon.level,
                ds_item_id(gen4_builder, mon.item) if mon.item else None,
                tuple(
                    gen4_builder.moves.move_id(move.removeprefix("MOVE_").lower().replace("_", "-"))
                    for move in mon.moves
                ),
            )
            for mon in trainers[number].party
        )
        if (places[const], party) not in displayed:
            missing.append((const, number, trainers[number].name, party))
    assert not missing, missing


def test_every_field_and_hidden_item_reaches_its_display(
    db: sqlite3.Connection, catalog: CharacterCatalog, gen4_builder: DatabaseBuilder, projection: Gen4MapProjection
) -> None:
    places = _places(db, catalog)
    displayed = set(
        db.execute(
            """SELECT coalesce(m.parent_map_id, m.id), o.kind, o.item_id, o.x, o.y FROM map_object o
           JOIN map m ON m.id = o.map_id WHERE o.kind IN ('item', 'hidden_item')"""
        )
    )
    expected = set()
    for item in catalog.items:
        const = catalog.headers[item.header]
        x, y = projection.point(const, item.x, item.z, item.y if item.kind == "item" else None)
        _, (dx, dy) = projection.maps.assembly_coordinates.get(const, (const, (0, 0)))
        expected.add((places[const], item.kind, ds_item_id(gen4_builder, item.item), x + dx, y + dy))
    assert not expected - displayed, expected - displayed


def test_multiple_item_quantities_are_annotated(
    db: sqlite3.Connection, catalog: CharacterCatalog, gen4_builder: DatabaseBuilder
) -> None:
    places = _places(db, catalog)
    displayed = set(
        db.execute(
            """SELECT coalesce(m.parent_map_id, m.id), o.kind, o.item_id, o.name_fr FROM map_object o
           JOIN map m ON m.id = o.map_id WHERE o.kind IN ('item', 'hidden_item')"""
        )
    )
    for item in catalog.items:
        number = ds_item_id(gen4_builder, item.item)
        name = db.execute("SELECT name_fr FROM item WHERE id = ?", (number,)).fetchone()[0]
        label = f"{name} ×{item.quantity}" if item.quantity > 1 else name
        assert (places[catalog.headers[item.header]], item.kind, number, label) in displayed


def test_validation_detects_a_lost_honey_quantity(db: sqlite3.Connection) -> None:
    query = next(query for label, query in CHECKS if label == "quantités des lots de Miel cachés de Platine perdues")
    assert not db.execute(query).fetchall()
    db.execute("UPDATE map_object SET name_fr = 'Miel' WHERE name_fr = 'Miel ×3'")
    assert len(db.execute(query).fetchall()) == 2


@pytest.mark.parametrize(
    "clear",
    ["DELETE FROM version_group WHERE id = 9", "DELETE FROM map WHERE version_group_id = 9", "DELETE FROM map_object"],
)
def test_honey_validation_allows_previews_without_items(db: sqlite3.Connection, clear: str) -> None:
    query = next(query for label, query in CHECKS if label == "quantités des lots de Miel cachés de Platine perdues")
    db.execute(clear)
    assert not db.execute(query).fetchall()


def test_every_offer_keeps_its_conditions_and_payment(
    db: sqlite3.Connection, catalog: CharacterCatalog, gen4_builder: DatabaseBuilder
) -> None:
    places = _places(db, catalog)
    species = dict(db.execute("SELECT identifier, id FROM pokemon"))
    versions = dict(db.execute("SELECT identifier, id FROM version"))
    rows = db.execute(
        """SELECT coalesce(m.parent_map_id, m.id), n.kind, n.item_id, n.pokemon_id, n.quantity,
                  n.price, n.wanted_pokemon_id, n.wanted_item_id, n.version_id, n.currency, s.description_fr
           FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           LEFT JOIN npc_offer_story s ON s.npc_offer_id = n.id"""
    )
    displayed: dict[tuple, set[str]] = defaultdict(set)
    for *key, story in rows:
        if story:
            displayed[tuple(key)].add(story)
        else:
            displayed[tuple(key)]
    missing = []
    for index, step in enumerate(catalog.offers.steps):
        for offer in actor_offers(gen4_builder, catalog, (index,)):
            key = (
                places[step.site.header],
                offer.kind,
                gen4_builder.items.ids.get(offer.item),
                species.get(offer.pokemon),
                offer.quantity,
                offer.price,
                species.get(offer.wanted),
                gen4_builder.items.ids.get(offer.wanted_item),
                versions.get(offer.version),
                offer.currency,
            )
            if key not in displayed or not set(offer.stories) <= displayed[key]:
                missing.append((step.site.header, step.step, key, offer.stories))
    assert not missing, missing


def test_all_encounter_rows_and_conditions_match_the_distributed_database(
    db: sqlite3.Connection, gen4_builder: DatabaseBuilder
) -> None:
    complete_preview_encounters(gen4_builder)
    conditions: dict[int, list[int]] = defaultdict(list)
    for encounter, condition in db.execute(
        "SELECT encounter_id, condition_value_id FROM encounter_condition ORDER BY condition_value_id"
    ):
        conditions[encounter].append(condition)
    rows = db.execute(
        """SELECT id, version_id, location_area_id, pokemon_id, method_id, min_level, max_level,
                  round(chance, 6), quantity, external_event FROM encounter WHERE version_id IN (12, 13, 14)"""
    )
    actual = {(*row[1:], tuple(conditions[row[0]])) for row in rows}
    expected = {
        (
            group.version_id,
            group.location_area_id,
            group.pokemon_id,
            group.method_id,
            group.min_level,
            group.max_level,
            round(group.chance, 6) if group.chance is not None else None,
            group.quantity,
            int(group.external_event),
            group.conditions,
        )
        for group in gen4_builder.encounters.encounter_groups
    }
    assert actual == expected
    rates = set(
        db.execute(
            """SELECT version_id, location_area_id, method_id, rate FROM encounter_rate
           WHERE version_id IN (12, 13, 14)"""
        )
    )
    assert {row for data in gen4_builder.encounters.gen4_wild.values() for row in data.rates} <= rates


def test_every_encounter_area_is_linked_to_a_distributed_map(db: sqlite3.Connection) -> None:
    missing = db.execute(
        """SELECT DISTINCT v.identifier, e.location_area_id, em.identifier FROM encounter e
           JOIN version v ON v.id = e.version_id JOIN encounter_method em ON em.id = e.method_id
           WHERE v.id IN (12, 13, 14) AND NOT EXISTS (
               SELECT 1 FROM map_area a JOIN map m ON m.id = a.map_id
               WHERE a.location_area_id = e.location_area_id AND m.version_group_id = v.version_group_id
           )"""
    ).fetchall()
    assert not missing, missing
