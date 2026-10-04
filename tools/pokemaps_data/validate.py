"""Contrôles de cohérence de pokedex.db, exécutés après chaque génération."""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Mew n'est obtenable que lors d'événements officiels.
EVENT_ONLY = {151}

# Requêtes qui doivent renvoyer 0 ligne : (description, requête).
ORPHAN_CHECKS = (
    ("attaque inconnue dans pokemon_move", "SELECT * FROM pokemon_move WHERE move_id NOT IN (SELECT id FROM move)"),
    (
        "Pokémon inconnu dans pokemon_move",
        "SELECT * FROM pokemon_move WHERE pokemon_id NOT IN (SELECT id FROM pokemon)",
    ),
    ("Pokémon inconnu dans evolution", "SELECT * FROM evolution WHERE to_pokemon_id NOT IN (SELECT id FROM pokemon)"),
    ("objet inconnu dans evolution", "SELECT * FROM evolution WHERE item_id NOT IN (SELECT id FROM item)"),
    ("lieu inconnu dans encounter", "SELECT * FROM encounter WHERE location_id NOT IN (SELECT id FROM location)"),
    ("Pokémon inconnu dans encounter", "SELECT * FROM encounter WHERE pokemon_id NOT IN (SELECT id FROM pokemon)"),
    ("version inconnue dans encounter", "SELECT * FROM encounter WHERE version_id NOT IN (SELECT id FROM version)"),
    ("type inconnu", "SELECT * FROM pokemon WHERE type1_id NOT IN (SELECT id FROM type)"),
    ("type d'attaque inconnu", "SELECT * FROM move WHERE type_id NOT IN (SELECT id FROM type)"),
    ("attaque inconnue dans machine", "SELECT * FROM machine WHERE move_id NOT IN (SELECT id FROM move)"),
    ("nom français vide", "SELECT * FROM pokemon WHERE trim(name_fr) = '' OR trim(genus_fr) = ''"),
    ("nom d'attaque vide", "SELECT * FROM move WHERE trim(name_fr) = ''"),
    ("Pokémon sans attaque", "SELECT id FROM pokemon WHERE id NOT IN (SELECT pokemon_id FROM pokemon_move)"),
    (
        "taux de rencontre aléatoire incohérent",
        """SELECT version_id, location_id, method, round(sum(chance), 1) AS total FROM encounter
           WHERE method IN ('WALK', 'SURF', 'OLD_ROD', 'GOOD_ROD', 'SUPER_ROD')
           GROUP BY version_id, location_id, method HAVING abs(total - 100) > 0.1""",
    ),
)


def validate(path: Path) -> list[str]:
    """Renvoie la liste des erreurs détectées (vide si tout est cohérent)."""
    errors: list[str] = []
    connection = sqlite3.connect(path)
    try:
        count = connection.execute("SELECT count(*) FROM pokemon").fetchone()[0]
        if count != 151:
            errors.append(f"{count} Pokémon au lieu de 151")
        moves = connection.execute("SELECT count(*) FROM move").fetchone()[0]
        if moves != 165:
            errors.append(f"{moves} attaques au lieu de 165")
        machines = connection.execute("SELECT count(*) FROM machine").fetchone()[0]
        if machines != 55:
            errors.append(f"{machines} CT/CS au lieu de 55")
        for description, query in ORPHAN_CHECKS:
            rows = connection.execute(query).fetchall()
            if rows:
                errors.append(f"{description} : {rows[:5]}")
        # Les exclusivités de version s'obtiennent par échange : on vérifie l'ensemble des versions.
        versions = [row[0] for row in connection.execute("SELECT id FROM version")]
        missing = set.intersection(*(_unobtainable(connection, version_id) for version_id in versions))
        if missing - EVENT_ONLY:
            errors.append(f"Pokémon impossibles à obtenir dans toutes les versions : {sorted(missing)}")
    finally:
        connection.close()
    return errors


def _unobtainable(connection: sqlite3.Connection, version_id: int) -> set[int]:
    """Pokémon ni rencontrés ni obtenables par évolution d'un Pokémon rencontré dans la version."""
    query = "SELECT DISTINCT pokemon_id FROM encounter WHERE version_id = ?"
    obtainable = {row[0] for row in connection.execute(query, (version_id,))}
    evolutions = connection.execute("SELECT from_pokemon_id, to_pokemon_id FROM evolution").fetchall()
    changed = True
    while changed:
        changed = False
        for source, target in evolutions:
            if source in obtainable and target not in obtainable:
                obtainable.add(target)
                changed = True
    every = {row[0] for row in connection.execute("SELECT id FROM pokemon")}
    return every - obtainable
