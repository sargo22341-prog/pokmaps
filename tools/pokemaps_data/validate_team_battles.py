"""Invariants hors ligne des équipes ennemies et des combats de Jessie et James."""

import sqlite3


def validate_team_battles(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """SELECT v.identifier, m.identifier, o.kind, o.sprite, o.name_fr,
                  (SELECT count(*) FROM trainer_pokemon p WHERE p.map_object_id = o.id), o.trainer_class
           FROM map_object o JOIN map m ON m.id = o.map_id
           LEFT JOIN version v ON v.id = o.version_id"""
    ).fetchall()
    errors = []
    for version, label, kind, sprite, _, count, trainer_class in rows:
        if version not in {"ruby", "sapphire", "emerald"} or kind != "trainer":
            continue
        team = next((team for team in ("aqua", "magma") if team.upper() in (trainer_class or "")), None)
        if team and (count == 0 or not _matches_team(team, sprite)):
            errors.append(f"{version}:{label} : combat ennemi sans équipe ou avec une apparence incorrecte")
    for version, team in (("ruby", "magma"), ("sapphire", "aqua"), ("emerald", "aqua")):
        for floor, count in (("1f", 2), ("2f", 4 if version == "emerald" else 3)):
            label = "route119-weather-institute-" + floor
            actors = [row for row in rows if row[0] == version and row[1] == label and row[2] == "trainer"]
            if len(actors) != count or any(team not in (row[3] or "") or row[5] == 0 for row in actors):
                errors.append(f"{version}:{label} : sbires, apparences ou équipes incorrects")
        if version != "emerald":
            for floor, count in (("1f", 1), ("b1f", 3), ("b2f", 3)):
                label = "magma-hideout-" + floor
                actors = [row for row in rows if row[0] == version and row[1] == label and row[2] == "trainer"]
                if len(actors) != count:
                    errors.append(f"{version}:{label} : combats du repaire manquants")
    for label in ("mt-moon-b2f", "rocket-hideout-b4f", "pokemon-tower-7f", "silph-co-11f"):
        actors = [row for row in rows if row[1] == label and row[3] == "jessie"]
        partners = [row for row in rows if row[1] == label and row[3] == "james"]
        if (
            len(actors) != 1
            or actors[0][2] != "trainer"
            or actors[0][4] != "Jessie et James"
            or actors[0][5] != 3
            or len(partners) != 1
            or partners[0][2] != "npc"
        ):
            errors.append(f"yellow:{label} : combat de Jessie et James incomplet")
    return errors + _weather_gifts(connection) + _yellow_fixed_rivals(connection)


def _matches_team(team: str, sprite: str | None) -> bool:
    return team in (sprite or "") or (team, sprite) in {
        ("aqua", "obj-event-gfx-archie"),
        ("magma", "obj-event-gfx-maxie"),
    }


def _weather_gifts(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """SELECT v.identifier, o.kind, o.sprite, n.kind, p.identifier FROM npc_offer n
           JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
           WHERE m.identifier = 'route119-weather-institute-2f'"""
    ).fetchall()
    errors = []
    for version in ("ruby", "sapphire", "emerald"):
        offers = [row[1:] for row in rows if row[0] == version]
        if offers != [("npc", "obj-event-gfx-scientist-1", "gift_pokemon", "castform")]:
            errors.append(f"{version} : don de Morphéo attribué au mauvais personnage ou service de surnom erroné")
    return errors


def _yellow_fixed_rivals(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """SELECT m.identifier, count(t.slot) FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version_group vg ON vg.id = m.version_group_id
           LEFT JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE vg.identifier = 'yellow' AND o.sprite = 'blue' GROUP BY o.id"""
    ).fetchall()
    errors = []
    for label, size in (("oaks-lab", 1), ("route-22", 2), ("cerulean-city", 4), ("ss-anne-2f", 4)):
        if [count for place, count in rows if place == label] != [size]:
            errors.append(f"yellow:{label} : équipe fixe du rival manquante ou incomplète")
    return errors
