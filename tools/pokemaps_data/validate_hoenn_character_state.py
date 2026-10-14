"""Invariants de l'état affiché des personnages de Hoenn dans la base distribuée."""

from __future__ import annotations

import sqlite3


def validate_hoenn_characters(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """SELECT v.identifier, m.identifier, o.kind, o.sprite, o.name_fr
           FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version v ON v.id = o.version_id
           WHERE v.identifier IN ('ruby', 'sapphire', 'emerald')"""
    ).fetchall()
    errors = []
    for version in ("ruby", "sapphire", "emerald"):
        actors = [row[1:] for row in rows if row[0] == version]
        errors.extend(_check_version(version, actors))
    return errors + _check_rival_teams(connection)


def _check_rival_teams(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute(
        """SELECT v.identifier, m.identifier, count(DISTINCT t.team),
                  count(DISTINCT t.variant_pokemon_id)
           FROM map_object o JOIN map m ON m.id = o.map_id JOIN version v ON v.id = o.version_id
           LEFT JOIN trainer_pokemon t ON t.map_object_id = o.id
           WHERE v.identifier IN ('ruby', 'sapphire', 'emerald')
             AND o.kind = 'trainer' AND o.name_fr = 'Flora' GROUP BY o.id"""
    ).fetchall()
    return [
        f"{version}:{label} : trois équipes de Flora selon le partenaire du joueur attendues"
        for version, label, teams, partners in rows
        if (teams, partners) != (3, 3)
    ]


def _check_version(version: str, actors: list[tuple[str, str, str | None, str]]) -> list[str]:
    errors = []
    for label, kind, sprite, name in actors:
        if sprite == "obj-event-gfx-prof-birch" and label != "littleroot-town-professor-birchs-lab":
            errors.append(f"{version}:{label} : Seko hors du laboratoire")
        if label == "route101" and sprite in {
            "obj-event-gfx-birchs-bag",
            "obj-event-gfx-poochyena",
            "obj-event-gfx-zigzagoon-1",
        }:
            errors.append(f"{version}:{label} : acteur d'introduction")
        if label.startswith("littleroot-town") and (
            sprite == "obj-event-gfx-truck"
            or (sprite and "carrying-box" in sprite)
            or (sprite and "facing-away" in sprite)
            or sprite == "obj-event-gfx-rival-brendan-normal"
            or (kind == "npc" and sprite is None)
        ):
            errors.append(f"{version}:{label} : acteur incompatible avec le héros garçon")
        if kind == "trainer" and name == "Flora" and sprite != "obj-event-gfx-rival-may-normal":
            errors.append(f"{version}:{label} : apparence de la rivale incorrecte")
    required = {"route103", "route110", "route119", "lilycove-city"}
    if version == "emerald":
        required |= {"rustboro-city"}
    for label in sorted(required):
        count = sum(map_name == label and kind == "trainer" and name == "Flora" for map_name, kind, _, name in actors)
        if count != 1:
            errors.append(f"{version}:{label} : {count} combats affichés pour la rivale, un attendu")
    return errors + _check_houses(version, actors) + _check_reporters(version, actors)


def _check_reporters(version: str, actors: list[tuple[str, str, str | None, str]]) -> list[str]:
    errors = []
    for label in ("route111", "route118", "route120"):
        for sprite in ("obj-event-gfx-cameraman", "obj-event-gfx-reporter-f"):
            count = sum(map_name == label and graphic == sprite for map_name, _, graphic, _ in actors)
            if count != 1:
                errors.append(f"{version}:{label}:{sprite} : {count} journalistes affichés, un attendu")
    return errors


def _check_houses(version: str, actors: list[tuple[str, str, str | None, str]]) -> list[str]:
    populations = {
        "littleroot-town-brendans-house-1f": ["obj-event-gfx-mom"],
        "littleroot-town-brendans-house-2f": [],
        "littleroot-town-mays-house-1f": (
            ["obj-event-gfx-woman-4", "obj-event-gfx-ninja-boy"] if version == "emerald" else ["obj-event-gfx-woman-5"]
        ),
        "littleroot-town-mays-house-2f": ["obj-event-gfx-rival-may-normal"],
    }
    errors = []
    for label, expected in populations.items():
        actual = [sprite for map_name, kind, sprite, _ in actors if map_name == label and kind == "npc"]
        if sorted(actual, key=str) != sorted(expected):
            errors.append(f"{version}:{label} : habitants incorrects : {actual}")
    if sum(sprite == "obj-event-gfx-prof-birch" for _, _, sprite, _ in actors) != 1:
        errors.append(f"{version} : un seul Seko attendu dans le laboratoire")
    if sum(label == "littleroot-town" and kind == "npc" for label, kind, _, _ in actors) != 3:
        errors.append(f"{version}:littleroot-town : trois PNJ de base attendus")
    return errors
