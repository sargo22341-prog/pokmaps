"""Contrôles de cohérence de pokedex.db, exécutés après chaque génération."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .builder_pokemon import BREEDING_GENERATION
from .games import DECLARED_GAMES, EXTERNAL_EVENT_AREAS, EXTERNAL_EVENT_LOCATIONS, EXTERNAL_EVENT_METHODS
from .sources import DATA_DIR

# Groupe d'œufs des Pokémon qui ne se reproduisent pas (légendaires, bébés).
_NO_EGGS = "no-eggs"

# Requêtes qui doivent renvoyer 0 ligne : (description, requête).
CHECKS = (
    (
        "méthode de rencontre non prise en charge",
        """SELECT id, identifier FROM encounter_method WHERE identifier NOT IN
           ('walk', 'old-rod', 'good-rod', 'super-rod', 'feebas-tile-fishing', 'surf', 'seaweed',
            'headbutt', 'headbutt-low', 'headbutt-normal', 'headbutt-high', 'rock-smash',
            'gift', 'gift-egg', 'colosseum-bonus-disc-jpn', 'colosseum-bonus-disc-us', 'pokemon-channel-pal',
            'static', 'pokeflute', 'squirt-bottle', 'roaming-grass', 'roaming-water',
            'devon-scope', 'wailmer-pail', 'npc-trade')""",
    ),
    (
        "méthode d'apprentissage non prise en charge",
        """SELECT pokemon_id, method FROM pokemon_move
           WHERE method NOT IN
           ('level-up', 'machine', 'egg', 'tutor', 'light-ball-egg', 'stadium-surfing-pikachu')""",
    ),
    (
        "génération d'origine du remake invalide",
        """SELECT * FROM version_group WHERE remake_generation_id IS NOT NULL
           AND (remake_generation_id >= generation_id
                OR remake_generation_id NOT IN (SELECT id FROM generation))""",
    ),
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
    (
        "Pokémon inconnu dans evolution",
        """SELECT * FROM evolution
           WHERE from_pokemon_id NOT IN (SELECT id FROM pokemon) OR to_pokemon_id NOT IN (SELECT id FROM pokemon)""",
    ),
    (
        "espèce d'origine inconnue",
        "SELECT id, evolves_from_id FROM pokemon WHERE evolves_from_id NOT IN (SELECT id FROM pokemon)",
    ),
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
    (
        "Pokémon d'un Pokédex postérieur à la génération du jeu",
        """SELECT vg.identifier, pe.pokedex_id, p.id FROM pokedex_entry pe
           JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
           JOIN version_group vg ON vg.id = vgp.version_group_id JOIN pokemon p ON p.id = pe.pokemon_id
           WHERE p.generation_id > vg.generation_id""",
    ),
    (
        "Pokémon rencontré absent des Pokédex de son jeu",
        """SELECT DISTINCT vg.identifier, e.pokemon_id FROM encounter e JOIN version v ON v.id = e.version_id
           JOIN version_group vg ON vg.id = v.version_group_id
           WHERE NOT EXISTS (SELECT 1 FROM pokedex_entry pe
                             JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
                             WHERE vgp.version_group_id = vg.id AND pe.pokemon_id = e.pokemon_id)""",
    ),
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
        "données d'espèce par jeu absentes ou invalides",
        """SELECT p.id, vg.id FROM pokemon p JOIN version_group vg ON vg.generation_id >= p.generation_id
           LEFT JOIN pokemon_version_group pv ON pv.pokemon_id = p.id AND pv.version_group_id = vg.id
           WHERE pv.pokemon_id IS NULL OR pv.capture_rate NOT BETWEEN 1 AND 255 OR pv.hatch_counter <= 0
             OR (pv.hatch_counter IS NULL) != (vg.generation_id < 2)
           UNION ALL
           SELECT pv.pokemon_id, pv.version_group_id FROM pokemon_version_group pv
           LEFT JOIN pokemon p ON p.id = pv.pokemon_id LEFT JOIN version_group vg ON vg.id = pv.version_group_id
           WHERE p.id IS NULL OR vg.id IS NULL OR p.generation_id > vg.generation_id""",
    ),
    (
        "description du Pokédex sans jeu d'origine",
        """SELECT id FROM pokemon
           WHERE (description_fr IS NULL) != (description_version_fr IS NULL) OR trim(description_version_fr) = ''""",
    ),
    (
        "rencontre avec niveaux, quantité ou probabilité invalides",
        """SELECT e.id FROM encounter e JOIN encounter_method m ON m.id = e.method_id
           WHERE e.min_level NOT BETWEEN 1 AND 100 OR e.max_level NOT BETWEEN e.min_level AND 100
             OR e.quantity < 1 OR (m.is_one_off = 0 AND (e.chance IS NULL OR e.chance <= 0 OR e.chance > 100))
             OR (m.is_one_off = 1 AND e.chance IS NOT NULL)""",
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
        "région ou origine de carte invalide",
        """SELECT m.id FROM map m
           LEFT JOIN map o ON o.id = m.origin_map_id
           LEFT JOIN map s ON s.id = m.start_map_id
           LEFT JOIN map p ON p.id = m.parent_map_id
           WHERE m.is_world NOT IN (0, 1)
             OR (m.is_world = 1 AND (m.parent_map_id IS NOT NULL OR m.origin_map_id IS NOT NULL
                 OR s.id IS NULL OR s.parent_map_id IS NULL OR s.parent_map_id != m.id))
             OR (m.is_world = 0 AND m.start_map_id IS NOT NULL)
             OR (m.parent_map_id IS NOT NULL AND (p.id IS NULL OR p.level_count <= 0))
             OR (m.origin_map_id IS NOT NULL AND (o.id IS NULL OR o.parent_map_id IS NULL
                 OR o.version_group_id != m.version_group_id))
             OR (m.is_world = 0 AND m.parent_map_id IS NULL AND m.origin_map_id IS NULL)""",
    ),
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
        "carte propre à une version hors de son groupe ou contredisant sa carte affichée",
        """SELECT m.id FROM map m
           LEFT JOIN version v ON v.id = m.version_id
           LEFT JOIN map p ON p.id = m.parent_map_id
           WHERE (m.version_id IS NOT NULL AND (v.id IS NULL OR v.version_group_id != m.version_group_id
                  OR m.is_world = 1))
             OR (p.version_id IS NOT NULL AND (m.version_id IS NULL OR m.version_id != p.version_id))""",
    ),
    (
        "objet de carte d'une autre version que sa carte",
        """SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE m.version_id IS NOT NULL AND o.version_id IS NOT NULL AND o.version_id != m.version_id""",
    ),
    (
        "passage sans warp de type inconnu ou mal relié",
        """SELECT w.id FROM map_warp w JOIN map m ON m.id = w.map_id
           LEFT JOIN map t ON t.id = w.target_map_id
           WHERE (w.kind IS NOT NULL AND w.kind NOT IN ('dive', 'cable_car', 'mirage', 'secret_base'))
             OR (w.kind IS NOT NULL AND (t.id IS NULL OR w.target_x IS NULL OR w.target_y IS NULL))
             OR (w.kind = 'secret_base' AND t.identifier NOT LIKE 'secret-base-%')
             OR (coalesce(w.kind, '') != 'secret_base' AND t.identifier LIKE 'secret-base-%'
                 AND m.identifier NOT LIKE 'secret-base-%')
             OR (m.version_id IS NOT NULL AND t.version_id IS NOT NULL AND m.version_id != t.version_id)""",
    ),
    (
        "objet de carte incohérent",
        """SELECT o.id FROM map_object o JOIN map m ON m.id = o.map_id
           WHERE o.kind NOT IN ('item', 'hidden_item', 'trainer', 'pokemon', 'npc', 'npc_object', 'npc_pokemon',
               'vending_machine', 'prize_vendor', 'heal_spot')
             OR (o.kind IN ('npc', 'npc_object', 'npc_pokemon') AND (o.trainer_class IS NOT NULL
               OR (o.sprite IS NULL AND m.version_group_id NOT IN
                   (SELECT id FROM version_group WHERE generation_id = 3))))
             OR (o.kind IN ('item', 'hidden_item')) != (o.item_id IS NOT NULL)
             OR (o.kind IN ('vending_machine', 'prize_vendor', 'heal_spot') AND (o.sprite IS NOT NULL
               OR NOT EXISTS (SELECT 1 FROM npc_offer n WHERE n.map_object_id = o.id)))
             OR (o.kind = 'heal_spot' AND EXISTS (SELECT 1 FROM npc_offer n WHERE n.map_object_id = o.id
               AND n.kind != 'heal'))
             OR (o.kind = 'pokemon') != (o.pokemon_id IS NOT NULL AND o.level IS NOT NULL)
             OR (o.kind = 'trainer') != (o.trainer_class IS NOT NULL) OR trim(o.name_fr) = ''
             OR o.item_id NOT IN (SELECT id FROM item) OR o.pokemon_id NOT IN (SELECT id FROM pokemon)
             OR o.x NOT BETWEEN m.x AND m.x + m.width OR o.y NOT BETWEEN m.y AND m.y + m.height
             OR (o.version_id IS NOT NULL AND o.version_id NOT IN
               (SELECT v.id FROM version v WHERE v.version_group_id = m.version_group_id))""",
    ),
    (
        "équipe de dresseur incohérente",
        """SELECT t.* FROM trainer_pokemon t LEFT JOIN map_object o ON o.id = t.map_object_id
           WHERE o.kind IS NOT 'trainer' OR t.pokemon_id NOT IN (SELECT id FROM pokemon)
             OR t.level NOT BETWEEN 1 AND 100 OR t.move1_id IS NULL OR t.team < 1
             OR (t.variant_kind IS NULL) != (t.variant_pokemon_id IS NULL)
             OR t.variant_kind NOT IN ('player-starter', 'rival-evolution')
             OR t.variant_pokemon_id NOT IN (SELECT id FROM pokemon)""",
    ),
    (
        "variantes d'équipe incohérentes (une seule équipe nommée, équipes non numérotées de 1 à n ou mélangées)",
        """SELECT map_object_id FROM trainer_pokemon GROUP BY map_object_id
           HAVING count(DISTINCT team) != max(team)
             OR count(DISTINCT coalesce(variant_kind, '') || '/' || coalesce(variant_pokemon_id, '')) != max(team)
             OR (max(team) = 1) != (max(variant_kind) IS NULL)
             OR count(DISTINCT variant_kind) > 1""",
    ),
    (
        "attaque de dresseur sans caractéristiques dans le jeu",
        """SELECT t.map_object_id, t.slot, mv.move_id FROM trainer_pokemon t
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           JOIN (SELECT map_object_id, team, slot, move1_id AS move_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, team, slot, move2_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, team, slot, move3_id FROM trainer_pokemon
                 UNION ALL SELECT map_object_id, team, slot, move4_id FROM trainer_pokemon) mv
             ON mv.map_object_id = t.map_object_id AND mv.team = t.team AND mv.slot = t.slot
             AND mv.move_id IS NOT NULL
           LEFT JOIN move_version_group mvg ON mvg.move_id = mv.move_id AND mvg.version_group_id = m.version_group_id
           WHERE mvg.move_id IS NULL""",
    ),
    (
        "offre de personnage incohérente",
        """SELECT n.* FROM npc_offer n LEFT JOIN map_object o ON o.id = n.map_object_id
           LEFT JOIN map m ON m.id = o.map_id
           WHERE o.id IS NULL
             OR n.kind NOT IN ('gift_item', 'gift_pokemon', 'gift_egg', 'sale', 'trade', 'exchange', 'prize_item',
               'prize_pokemon', 'coin_sale', 'coin_gift', 'fossil', 'fruit_tree', 'heal', 'cable_club', 'name_rater',
               'daycare', 'daycare_egg', 'daycare_withdrawal', 'move_relearner',
               'move_deleter', 'grooming', 'move_tutor', 'point_prize')
             OR (n.kind IN ('gift_item', 'sale', 'exchange', 'prize_item', 'point_prize', 'fossil', 'fruit_tree')
               AND n.item_id IS NULL)
             OR (n.kind NOT IN ('gift_item', 'sale', 'exchange', 'prize_item', 'point_prize', 'fossil', 'fruit_tree',
               'gift_pokemon', 'trade') AND n.item_id IS NOT NULL)
             OR (n.kind IN ('gift_pokemon', 'gift_egg', 'trade', 'prize_pokemon', 'fossil'))
               != (n.pokemon_id IS NOT NULL)
             OR (n.kind = 'trade') != (n.wanted_pokemon_id IS NOT NULL)
             OR (n.kind IN ('exchange', 'move_relearner')) != (n.wanted_item_id IS NOT NULL)
             OR (n.kind IN ('prize_item', 'prize_pokemon', 'point_prize', 'coin_sale')
               AND coalesce(n.price, 0) <= 0)
             OR (n.kind = 'move_tutor' AND n.price IS NOT NULL AND n.price <= 0)
             OR (n.kind = 'move_tutor' AND n.price IS NULL AND m.version_group_id NOT IN
               (SELECT id FROM version_group WHERE generation_id = 3))
             OR n.currency NOT IN ('money', 'coins', 'battle_points', 'ashes')
             OR (n.currency IS NOT NULL AND n.kind NOT IN
               ('sale', 'prize_item', 'prize_pokemon', 'coin_sale', 'daycare_withdrawal', 'move_tutor'))
             OR (n.kind = 'prize_pokemon' AND n.currency IS NOT NULL AND n.currency != 'coins')
             OR (n.kind = 'sale' AND n.currency IS NOT NULL AND coalesce(n.price, 0) <= 0)
             OR (n.kind IN ('daycare_egg', 'daycare_withdrawal', 'move_relearner')
               AND coalesce(n.quantity, n.pokemon_id) IS NOT NULL)
             OR (n.kind IN ('prize_pokemon', 'coin_sale', 'coin_gift', 'fossil', 'gift_egg')
               AND coalesce(n.quantity, 0) <= 0)
             OR (n.kind IN ('fruit_tree', 'heal', 'cable_club', 'name_rater', 'daycare', 'move_deleter')
               AND coalesce(n.pokemon_id, n.quantity, n.price) IS NOT NULL)
             OR (n.kind = 'grooming' AND (coalesce(n.pokemon_id, n.quantity) IS NOT NULL OR n.price <= 0))
             OR (n.kind = 'move_tutor' AND coalesce(n.pokemon_id, n.quantity) IS NOT NULL)
             OR (n.version_id IS NOT NULL AND n.version_id NOT IN
               (SELECT v.id FROM version v WHERE v.version_group_id = m.version_group_id))
             OR n.item_id NOT IN (SELECT id FROM item) OR n.wanted_item_id NOT IN (SELECT id FROM item)
             OR n.pokemon_id NOT IN (SELECT id FROM pokemon)
             OR n.time_mask NOT BETWEEN 1 AND 6 OR n.weekday_mask NOT BETWEEN 1 AND 126
             OR (coalesce(n.time_mask, n.weekday_mask) IS NOT NULL AND m.version_group_id IN
               (SELECT vg.id FROM version_group vg JOIN generation g ON g.id = vg.generation_id
                WHERE g.identifier = 'generation-i'))""",
    ),
    (
        "étape du scénario d'une offre incohérente",
        """SELECT s.* FROM npc_offer_story s LEFT JOIN npc_offer n ON n.id = s.npc_offer_id
           WHERE n.id IS NULL OR trim(s.description_fr) = '' OR s.slot < 1
             OR s.slot > (SELECT count(*) FROM npc_offer_story o WHERE o.npc_offer_id = s.npc_offer_id)
             OR EXISTS (SELECT 1 FROM npc_offer_story o WHERE o.npc_offer_id = s.npc_offer_id
               AND o.slot != s.slot AND o.description_fr = s.description_fr)""",
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
        """SELECT peg.* FROM pokemon_egg_group peg LEFT JOIN pokemon p ON p.id = peg.pokemon_id
           LEFT JOIN version_group vg ON vg.id = peg.version_group_id
           WHERE p.id IS NULL OR vg.id IS NULL OR vg.generation_id < 2 OR p.generation_id > vg.generation_id
             OR peg.egg_group_id NOT IN (SELECT id FROM egg_group)""",
    ),
    (
        "Pokémon sans groupe d'œufs dans un jeu qui connaît la reproduction",
        """SELECT p.id, vg.id FROM pokemon p JOIN version_group vg ON vg.generation_id >= max(p.generation_id, 2)
           WHERE NOT EXISTS (SELECT 1 FROM pokemon_egg_group peg
                             WHERE peg.pokemon_id = p.id AND peg.version_group_id = vg.id)""",
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
           WHERE s.kind NOT IN ('grass', 'water', 'floor', 'tree', 'rock', 'underwater')
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
    """Chaque Pokémon des Pokédex (régional et, s'il y en a un, National) des jeux d'une branche doit être obtenable
    dans au moins une de leurs versions (rencontre hors événement externe, évolution ou, à partir de la 2e génération,
    reproduction), sauf les Pokémon fabuleux, distribués lors d'événements, et ceux qu'on n'obtient que par échange
    avec un autre jeu (tools/data/transfer_only.csv). Une branche réunit les jeux d'une famille de cartes : la
    3e génération en a deux (Hoenn, Remake 1G), qui ne s'obtiennent rien l'une pour l'autre."""
    errors = []
    transfers = _transfer_only(connection)
    for branch, (generation, groups) in _branches(connection).items():
        marks = ", ".join("?" * len(groups))
        expected = {
            row[0]
            for row in connection.execute(
                f"""SELECT DISTINCT pe.pokemon_id FROM pokedex_entry pe
                    JOIN version_group_pokedex vgp ON vgp.pokedex_id = pe.pokedex_id
                    JOIN pokemon p ON p.id = pe.pokemon_id
                    WHERE vgp.version_group_id IN ({marks}) AND p.is_mythical = 0""",
                groups,
            )
        }
        obtainable = _obtainable(connection, generation, groups)
        allowed = transfers.get(branch, set())
        if missing := expected - obtainable - allowed:
            errors.append(f"Branche {branch} : Pokémon impossibles à obtenir : {sorted(missing)}")
        if stale := sorted(allowed & obtainable):
            errors.append(f"transfer_only.csv : Pokémon obtenables dans la branche {branch} : {stale}")
    return errors


def _branches(connection: sqlite3.Connection) -> dict[str, tuple[int, tuple[int, ...]]]:
    """Branche (famille de cartes, games.py) -> génération et groupes de versions de la base qui en font partie."""
    families = {game.version_group: game.map_family for game in DECLARED_GAMES}
    branches: dict[str, tuple[int, tuple[int, ...]]] = {}
    for group_id, identifier, generation in connection.execute(
        "SELECT id, identifier, generation_id FROM version_group ORDER BY id"
    ):
        if identifier not in families:
            raise ValueError(f"Groupe de versions sans jeu déclaré dans games.py : {identifier}")
        family = families[identifier]
        known_generation, groups = branches.get(family, (generation, ()))
        if known_generation != generation:
            raise ValueError(f"Branche {family} sur deux générations : {known_generation} et {generation}")
        branches[family] = (generation, (*groups, group_id))
    return branches


def _obtainable(connection: sqlite3.Connection, generation: int, groups: tuple[int, ...]) -> set[int]:
    """Pokémon rencontrés dans les versions des groupes `groups` (hors événements externes), puis, jusqu'à stabilité,
    leurs évolutions et (à partir de BREEDING_GENERATION) le Pokémon de base de la famille de ceux qui peuvent pondre
    un œuf."""
    methods, places = sorted(EXTERNAL_EVENT_METHODS), sorted(EXTERNAL_EVENT_LOCATIONS)
    areas = sorted(EXTERNAL_EVENT_AREAS)
    obtainable = {
        row[0]
        for row in connection.execute(
            f"""SELECT DISTINCT e.pokemon_id FROM encounter e JOIN version v ON v.id = e.version_id
                JOIN encounter_method m ON m.id = e.method_id
                JOIN location_area la ON la.id = e.location_area_id JOIN location l ON l.id = la.location_id
                WHERE v.version_group_id IN ({", ".join("?" * len(groups))})
                  AND m.identifier NOT IN ({", ".join("?" * len(methods))})
                  AND l.identifier NOT IN ({", ".join("?" * len(places))})
                  AND l.identifier || '/' || la.identifier NOT IN ({", ".join("?" * len(areas))})""",
            (*groups, *methods, *places, *areas),
        )
    }
    links = _obtention_links(connection, generation, groups)
    changed = True
    while changed:
        changed = False
        for source, target in links:
            if source in obtainable and target not in obtainable:
                obtainable.add(target)
                changed = True
    return obtainable


def _obtention_links(connection: sqlite3.Connection, generation: int, groups: tuple[int, ...]) -> list[tuple[int, int]]:
    """(Pokémon obtenu, Pokémon qu'il permet d'obtenir) : évolutions des groupes `groups`, puis reproduction vers le
    plus petit Pokémon de la famille qui existe dans la génération (Marill pond Marill en 2e génération, où Azurill
    n'existe pas encore)."""
    links = connection.execute(
        f"""SELECT DISTINCT from_pokemon_id, to_pokemon_id FROM evolution
            WHERE version_group_id IN ({", ".join("?" * len(groups))})""",
        groups,
    ).fetchall()
    if generation >= BREEDING_GENERATION:
        links += connection.execute(
            f"""SELECT p.id, base.id FROM pokemon p
                JOIN pokemon base ON base.evolution_chain_id = p.evolution_chain_id AND base.generation_id <= ?
                 AND NOT EXISTS (SELECT 1 FROM pokemon prior
                                 WHERE prior.id = base.evolves_from_id AND prior.generation_id <= ?)
                WHERE NOT EXISTS (SELECT 1 FROM pokemon_egg_group peg JOIN egg_group g ON g.id = peg.egg_group_id
                                  WHERE peg.pokemon_id = p.id AND g.identifier = ?
                                    AND peg.version_group_id IN ({", ".join("?" * len(groups))}))""",
            (generation, generation, _NO_EGGS, *groups),
        ).fetchall()
    return links


def _transfer_only(connection: sqlite3.Connection) -> dict[str, set[int]]:
    """Branche -> Pokémon qu'on n'obtient qu'en les échangeant avec un autre jeu (tools/data/transfer_only.csv)."""
    families = {game.version_group: game.map_family for game in DECLARED_GAMES}
    species = dict(connection.execute("SELECT identifier, id FROM pokemon"))
    built = {row[0] for row in connection.execute("SELECT identifier FROM version_group")}
    result: dict[str, set[int]] = {}
    with (DATA_DIR / "transfer_only.csv").open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            # Une colonne en trop (virgule non protégée dans la raison) est rangée sous la clé None.
            if None in row or row["version_group"] not in families or not row["reason"].strip():
                raise ValueError(f"transfer_only.csv:{line} : jeu inconnu, raison manquante ou colonne en trop : {row}")
            if row["version_group"] not in built:
                continue
            if row["pokemon"] not in species:
                raise ValueError(f"transfer_only.csv:{line} : Pokémon inconnu : {row}")
            result.setdefault(families[row["version_group"]], set()).add(species[row["pokemon"]])
    return result
