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
    (
        "attaque apprise par CT/CS sans CT/CS dans le jeu",
        """SELECT pm.* FROM pokemon_move pm LEFT JOIN machine ma
           ON ma.move_id = pm.move_id AND ma.version_group_id = pm.version_group_id
           WHERE pm.method = 'machine' AND ma.item_id IS NULL""",
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
    (
        "zone avec des rencontres sans carte dans le jeu",
        """SELECT DISTINCT e.location_area_id, v.version_group_id FROM encounter e JOIN version v ON v.id = e.version_id
           WHERE NOT EXISTS (SELECT 1 FROM map_area ma JOIN map m ON m.id = ma.map_id
             WHERE ma.location_area_id = e.location_area_id AND m.version_group_id = v.version_group_id)""",
    ),
    ("zone de carte inconnue", "SELECT * FROM map_area WHERE location_area_id NOT IN (SELECT id FROM location_area)"),
    (
        "carte parente invalide",
        """SELECT m.id FROM map m JOIN map p ON p.id = m.parent_map_id
           WHERE p.parent_map_id IS NOT NULL OR p.version_group_id != m.version_group_id
             OR m.x < 0 OR m.y < 0 OR m.x + m.width > p.width OR m.y + m.height > p.height""",
    ),
    (
        "carte affichable sans niveau de zoom",
        "SELECT id FROM map WHERE (parent_map_id IS NULL) != (level_count > 0)",
    ),
    (
        "warp hors de sa carte ou vers une carte inconnue",
        """SELECT w.id FROM map_warp w JOIN map m ON m.id = w.map_id
           JOIN map d ON d.id = coalesce(m.parent_map_id, m.id)
           LEFT JOIN map t ON t.id = w.target_map_id
           WHERE w.x NOT BETWEEN m.x AND m.x + m.width OR w.y NOT BETWEEN m.y AND m.y + m.height
             OR (w.target_map_id IS NOT NULL AND (t.id IS NULL OR t.version_group_id != m.version_group_id))""",
    ),
    (
        "objet de carte incohérent",
        """SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE o.kind NOT IN ('item', 'hidden_item', 'trainer', 'pokemon', 'npc', 'npc_object', 'npc_pokemon',
               'vending_machine', 'prize_vendor')
             OR (o.kind IN ('npc', 'npc_object', 'npc_pokemon') AND (o.sprite IS NULL OR o.trainer_class IS NOT NULL))
             OR (o.kind IN ('item', 'hidden_item')) != (o.item_id IS NOT NULL)
             OR (o.kind IN ('vending_machine', 'prize_vendor') AND (o.sprite IS NOT NULL
               OR NOT EXISTS (SELECT 1 FROM npc_offer n WHERE n.map_object_id = o.id)))
             OR (o.kind = 'pokemon') != (o.pokemon_id IS NOT NULL AND o.level IS NOT NULL)
             OR (o.kind = 'trainer') != (o.trainer_class IS NOT NULL) OR trim(o.name_fr) = ''
             OR o.item_id NOT IN (SELECT id FROM item) OR o.pokemon_id NOT IN (SELECT id FROM pokemon)
             OR o.x NOT BETWEEN m.x AND m.x + m.width OR o.y NOT BETWEEN m.y AND m.y + m.height""",
    ),
    (
        "équipe de dresseur incohérente",
        """SELECT t.* FROM trainer_pokemon t LEFT JOIN map_object o ON o.id = t.map_object_id
           WHERE o.kind IS NOT 'trainer' OR t.pokemon_id NOT IN (SELECT id FROM pokemon)
             OR t.level NOT BETWEEN 1 AND 100 OR t.move1_id IS NULL""",
    ),
    (
        "attaque de dresseur sans caractéristiques dans le jeu",
        """SELECT t.map_object_id, t.slot, mv.move_id FROM trainer_pokemon t
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           JOIN (SELECT map_object_id, slot, move1_id AS move_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, slot, move2_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, slot, move3_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, slot, move4_id FROM trainer_pokemon) mv
             ON mv.map_object_id = t.map_object_id AND mv.slot = t.slot AND mv.move_id IS NOT NULL
           LEFT JOIN move_version_group mvg ON mvg.move_id = mv.move_id AND mvg.version_group_id = m.version_group_id
           WHERE mvg.move_id IS NULL""",
    ),
    (
        "offre de personnage incohérente",
        """SELECT n.* FROM npc_offer n LEFT JOIN map_object o ON o.id = n.map_object_id
           LEFT JOIN map m ON m.id = o.map_id
           WHERE o.id IS NULL
             OR n.kind NOT IN ('gift_item', 'gift_pokemon', 'sale', 'trade', 'exchange', 'prize_item',
               'prize_pokemon', 'coin_sale', 'coin_gift', 'fossil', 'heal', 'cable_club', 'name_rater', 'daycare')
             OR (n.kind IN ('gift_item', 'sale', 'exchange', 'prize_item', 'fossil')) != (n.item_id IS NOT NULL)
             OR (n.kind IN ('gift_pokemon', 'trade', 'prize_pokemon', 'fossil')) != (n.pokemon_id IS NOT NULL)
             OR (n.kind = 'trade') != (n.wanted_pokemon_id IS NOT NULL)
             OR (n.kind = 'exchange') != (n.wanted_item_id IS NOT NULL)
             OR (n.kind IN ('prize_item', 'prize_pokemon', 'coin_sale') AND coalesce(n.price, 0) <= 0)
             OR (n.kind IN ('prize_pokemon', 'coin_sale', 'coin_gift', 'fossil') AND coalesce(n.quantity, 0) <= 0)
             OR (n.kind IN ('heal', 'cable_club', 'name_rater', 'daycare')
               AND coalesce(n.item_id, n.pokemon_id, n.quantity, n.price) IS NOT NULL)
             OR (n.version_id IS NOT NULL AND n.version_id NOT IN
               (SELECT v.id FROM version v WHERE v.version_group_id = m.version_group_id))
             OR n.item_id NOT IN (SELECT id FROM item) OR n.wanted_item_id NOT IN (SELECT id FROM item)
             OR n.pokemon_id NOT IN (SELECT id FROM pokemon)""",
    ),
    (
        "jaquette de version incohérente",
        """SELECT id FROM version
           WHERE mascot_pokemon_id NOT IN (SELECT id FROM pokemon) OR color NOT BETWEEN 0 AND 16777215""",
    ),
    (
        "effet d'attaque vide ou probabilité invalide",
        """SELECT move_id, version_group_id FROM move_version_group
           WHERE trim(effect_fr) = ''
             OR (effect_chance IS NOT NULL AND (effect_chance <= 0 OR effect_chance >= 100))""",
    ),
    (
        "objet tenu incohérent",
        """SELECT pi.* FROM pokemon_item pi LEFT JOIN version v ON v.id = pi.version_id
           LEFT JOIN version_group vg ON vg.id = v.version_group_id
           WHERE vg.id IS NULL OR vg.generation_id < 2 OR pi.rarity NOT BETWEEN 1 AND 100
             OR pi.pokemon_id NOT IN (SELECT id FROM pokemon) OR pi.item_id NOT IN (SELECT id FROM item)""",
    ),
    (
        "groupe d'œufs incohérent",
        """SELECT * FROM pokemon_egg_group WHERE pokemon_id NOT IN (SELECT id FROM pokemon)
           OR egg_group_id NOT IN (SELECT id FROM egg_group)""",
    ),
    (
        "talent incohérent",
        """SELECT pa.* FROM pokemon_ability pa LEFT JOIN ability a ON a.id = pa.ability_id
           WHERE a.id IS NULL OR pa.generation_id < 3 OR a.generation_id > pa.generation_id
             OR pa.generation_id NOT IN (SELECT generation_id FROM version_group)
             OR pa.pokemon_id NOT IN (SELECT id FROM pokemon) OR trim(a.name_fr) = ''
             OR (pa.is_hidden = 1 AND pa.generation_id < 5)""",
    ),
    (
        "description de talent incohérente",
        """SELECT avg.* FROM ability_version_group avg LEFT JOIN version_group vg ON vg.id = avg.version_group_id
           LEFT JOIN ability a ON a.id = avg.ability_id
           WHERE vg.id IS NULL OR a.id IS NULL OR vg.generation_id < a.generation_id""",
    ),
    (
        "emplacement de Pokémon hors de sa carte",
        """SELECT s.id FROM map_spot s JOIN map m ON m.id = s.map_id
           WHERE s.kind NOT IN ('grass', 'water', 'floor')
             OR s.x NOT BETWEEN m.x AND m.x + m.width OR s.y NOT BETWEEN m.y AND m.y + m.height""",
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
