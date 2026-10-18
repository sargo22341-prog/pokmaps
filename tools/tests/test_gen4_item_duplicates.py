"""Les en-têtes DS peuvent partager un événement caché, sans dupliquer l'objet affiché."""

import sqlite3
from dataclasses import replace

from pokemaps_data.maps import GameMapData, MapRow
from pokemaps_data.maps_characters import ObjectRow
from pokemaps_data.maps_export_gen4 import _deduplicate_items
from pokemaps_data.validate import CHECKS


def test_shared_hidden_item_has_one_marker_but_distinct_items_remain() -> None:
    world = MapRow("SINNOH", 0, "Sinnoh", None, 0, 0, 1024, 1024, 1, is_world=True)
    city = replace(world, const="CITY", parent="SINNOH", is_world=False)
    route = replace(city, const="ROUTE")
    item = ObjectRow("CITY", "hidden_item", 20, 30, None, "stardust", None, None, None)
    other = replace(item, x=40)
    version = replace(item, version="pearl")
    npc = replace(item, kind="npc", item=None)
    data = GameMapData([world, city, route], [], [], [item, replace(item, map_const="ROUTE"), other, version, npc])
    _deduplicate_items(data)
    assert data.objects == [item, other, version, npc]


def test_validation_rejects_duplicate_across_parent_and_child(db: sqlite3.Connection) -> None:
    row = db.execute(
        """SELECT o.id, m.parent_map_id FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_group_id IN (8, 9) AND o.kind = 'hidden_item' AND m.parent_map_id IS NOT NULL LIMIT 1"""
    ).fetchone()
    db.execute(
        """INSERT INTO map_object SELECT (SELECT max(id) + 1 FROM map_object), ?, kind, x, y, sprite,
           item_id, pokemon_id, level, trainer_class, name_fr, version_id FROM map_object WHERE id = ?""",
        (row[1], row[0]),
    )
    query = next(query for description, query in CHECKS if description == "objet DS répété sur la même case affichée")
    assert db.execute(query).fetchall()
