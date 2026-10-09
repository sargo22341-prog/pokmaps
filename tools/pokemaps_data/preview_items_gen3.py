"""Écriture des métadonnées d'objets GBA, vérifiées contre la base de l'aperçu."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .maps_layout import identifier
from .pret_gen3_items import Gen3MapItem


def write_item_metadata(database: Path, output: Path, items: list[Gen3MapItem]) -> None:
    validate_item_metadata(database, items)
    output.write_text(
        json.dumps([asdict(item) for item in items], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def validate_item_metadata(database: Path, items: list[Gen3MapItem]) -> None:
    expected = Counter(
        (identifier(item.map_const), item.version, item.kind, item.x, item.y)
        for item in items
        if item.kind != "hidden_coins"
    )
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
    try:
        actual = Counter(
            connection.execute(
                "SELECT m.identifier, v.identifier, o.kind, o.x, o.y FROM map_object o "
                "JOIN map m ON m.id = o.map_id JOIN version v ON v.id = o.version_id "
                "WHERE o.kind IN ('item', 'hidden_item')"
            )
        )
    finally:
        connection.close()
    if expected != actual:
        raise ValueError(
            "Métadonnées des objets GBA incohérentes : "
            f"absents de la base : {list((expected - actual).elements())}, "
            f"absents du JSON : {list((actual - expected).elements())}"
        )
