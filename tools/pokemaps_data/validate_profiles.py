"""Invariants des formes et des provenances externes structurées."""

import sqlite3


def validate_profiles(connection: sqlite3.Connection) -> list[str]:
    checks = (
        (
            "forme sans version ou espèce",
            """SELECT f.identifier FROM pokemon_form f
          LEFT JOIN version v ON v.id = f.version_id LEFT JOIN pokemon p ON p.id = f.pokemon_id
          LEFT JOIN version_group vg ON vg.id = v.version_group_id
          WHERE v.id IS NULL OR p.id IS NULL OR p.generation_id > vg.generation_id""",
        ),
        (
            "forme par défaut absente ou ambiguë",
            """SELECT version_id, pokemon_id FROM pokemon_form
          GROUP BY version_id, pokemon_id HAVING sum(is_default) != 1""",
        ),
        (
            "profil de forme invalide",
            """SELECT identifier FROM pokemon_form WHERE
          is_default NOT IN (0, 1) OR sort_order < 0 OR trim(name_fr) = '' OR hp NOT BETWEEN 1 AND 255
          OR attack NOT BETWEEN 1 AND 255 OR defense NOT BETWEEN 1 AND 255
          OR special_attack NOT BETWEEN 1 AND 255 OR special_defense NOT BETWEEN 1 AND 255
          OR speed NOT BETWEEN 1 AND 255""",
        ),
        ("provenance de rencontre invalide", "SELECT id FROM encounter WHERE external_event NOT IN (0, 1)"),
        ("provenance d'offre invalide", "SELECT id FROM npc_offer WHERE external_event NOT IN (0, 1)"),
        (
            "entrée événementielle sans provenance",
            """SELECT id FROM map WHERE event_entrance < 0
          OR (event_entrance > 0 AND external_event_key IS NULL)""",
        ),
    )
    errors = []
    for label, query in checks:
        if rows := connection.execute(query).fetchall():
            errors.append(f"{label} : {rows[:5]}")
    return errors
