"""Contrôles de cohérence de pokedex.db, exécutés après chaque génération."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Requêtes qui doivent renvoyer 0 ligne : (description, requête).
CHECKS = (
    (
        "Pokémon inconnu dans pokemon_move",
        "SELECT * FROM pokemon_move WHERE pokemon_id NOT IN (SELECT id FROM pokemon)",
    ),
    ("attaque inconnue dans pokemon_move", "SELECT * FROM pokemon_move WHERE move_id NOT IN (SELECT id FROM move)"),
    (
        "attaque sans caractéristiques dans le jeu",
        """SELECT pm.* FROM pokemon_move pm LEFT JOIN move_version_group mvg
           ON mvg.move_id = pm.move_id AND mvg.version_group_id = pm.version_group_id WHERE mvg.move_id IS NULL""",
    ),
    ("type d'attaque inconnu", "SELECT * FROM move_version_group WHERE type_id NOT IN (SELECT id FROM type)"),
    ("CT/CS inconnue", "SELECT * FROM machine WHERE item_id NOT IN (SELECT id FROM item)"),
    ("Pokémon inconnu dans evolution", "SELECT * FROM evolution WHERE to_pokemon_id NOT IN (SELECT id FROM pokemon)"),
    ("objet inconnu dans evolution", "SELECT * FROM evolution WHERE item_id NOT IN (SELECT id FROM item)"),
    ("type de Pokémon inconnu", "SELECT * FROM pokemon_type WHERE type_id NOT IN (SELECT id FROM type)"),
    (
        "zone inconnue dans encounter",
        "SELECT * FROM encounter WHERE location_area_id NOT IN (SELECT id FROM location_area)",
    ),
    ("lieu inconnu", "SELECT * FROM location_area WHERE location_id NOT IN (SELECT id FROM location)"),
    ("Pokémon inconnu dans encounter", "SELECT * FROM encounter WHERE pokemon_id NOT IN (SELECT id FROM pokemon)"),
    ("méthode inconnue", "SELECT * FROM encounter WHERE method_id NOT IN (SELECT id FROM encounter_method)"),
    ("Pokémon du Pokédex inconnu", "SELECT * FROM pokedex_entry WHERE pokemon_id NOT IN (SELECT id FROM pokemon)"),
    ("nom français vide", "SELECT id FROM pokemon WHERE trim(name_fr) = '' OR trim(genus_fr) = ''"),
    ("nom d'attaque vide", "SELECT id FROM move WHERE trim(name_fr) = ''"),
    ("nom de zone vide", "SELECT id FROM location_area WHERE trim(name_fr) = ''"),
    ("Pokémon sans attaque", "SELECT id FROM pokemon WHERE id NOT IN (SELECT pokemon_id FROM pokemon_move)"),
    (
        "Pokémon sans type ou sans stats",
        """SELECT p.id, g.id FROM pokemon p JOIN generation g ON g.id >= p.generation_id
           WHERE g.id IN (SELECT generation_id FROM version_group)
           AND (NOT EXISTS (SELECT 1 FROM pokemon_type t WHERE t.pokemon_id = p.id AND t.generation_id = g.id)
             OR NOT EXISTS (SELECT 1 FROM pokemon_stat s WHERE s.pokemon_id = p.id AND s.generation_id = g.id))""",
    ),
    (
        "probabilités de rencontre aléatoire différentes de 100 %",
        """SELECT e.version_id, e.location_area_id, e.method_id, sum(e.chance) AS total FROM encounter e
           JOIN encounter_method m ON m.id = e.method_id WHERE m.is_one_off = 0
           GROUP BY e.version_id, e.location_area_id, e.method_id,
             (SELECT group_concat(condition_value_id) FROM encounter_condition c WHERE c.encounter_id = e.id)
           HAVING abs(total - 100) > 0.01""",
    ),
)


def validate(path: Path) -> list[str]:
    """Renvoie la liste des erreurs détectées (vide si tout est cohérent)."""
    errors: list[str] = []
    connection = sqlite3.connect(path)
    try:
        for description, query in CHECKS:
            rows = connection.execute(query).fetchall()
            if rows:
                errors.append(f"{description} : {rows[:5]}")
        errors += _check_obtainable(connection)
    finally:
        connection.close()
    return errors


def _check_obtainable(connection: sqlite3.Connection) -> list[str]:
    """Chaque Pokémon du Pokédex d'une génération doit être obtenable dans au moins une de ses versions
    (rencontre ou évolution), sauf les Pokémon fabuleux, distribués lors d'événements."""
    errors = []
    evolutions = connection.execute("SELECT version_group_id, from_pokemon_id, to_pokemon_id FROM evolution").fetchall()
    for (generation,) in connection.execute("SELECT DISTINCT generation_id FROM version_group").fetchall():
        expected = {
            row[0]
            for row in connection.execute(
                """SELECT DISTINCT pe.pokemon_id FROM pokedex_entry pe
                   JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
                   JOIN version_group vg ON vg.id = vgp.version_group_id
                   JOIN pokemon p ON p.id = pe.pokemon_id
                   WHERE vg.generation_id = ? AND p.is_mythical = 0""",
                (generation,),
            )
        }
        obtainable = {
            row[0]
            for row in connection.execute(
                """SELECT DISTINCT e.pokemon_id FROM encounter e JOIN version v ON v.id = e.version_id
                   JOIN version_group vg ON vg.id = v.version_group_id WHERE vg.generation_id = ?""",
                (generation,),
            )
        }
        groups = {
            row[0] for row in connection.execute("SELECT id FROM version_group WHERE generation_id = ?", (generation,))
        }
        changed = True
        while changed:
            changed = False
            for group, source, target in evolutions:
                if group in groups and source in obtainable and target not in obtainable:
                    obtainable.add(target)
                    changed = True
        missing = expected - obtainable
        if missing:
            errors.append(f"Génération {generation} : Pokémon impossibles à obtenir : {sorted(missing)}")
    return errors
