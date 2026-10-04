"""Contrôles de la base générée à partir des vraies sources (pret + PokéAPI)."""

from pokemaps_data.builder import SCHEMA_VERSION
from pokemaps_data.validate import validate

RED, BLUE, YELLOW = 1, 2, 3


def encounters(db, pokemon_id, version_id):
    return db.execute(
        """SELECT l.identifier, e.method, e.min_level, e.max_level, e.chance FROM encounter e
           JOIN location l ON l.id = e.location_id
           WHERE e.pokemon_id = ? AND e.version_id = ? ORDER BY l.identifier, e.method""",
        (pokemon_id, version_id),
    ).fetchall()


def test_validation_passes(database):
    assert validate(database) == []


def test_schema_version(db):
    assert db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION


def test_french_names(db):
    names = dict(db.execute("SELECT id, name_fr FROM pokemon WHERE id IN (1, 25, 122, 133)"))
    assert names == {1: "Bulbizarre", 25: "Pikachu", 122: "M. Mime", 133: "Évoli"}


def test_route_1_red(db):
    rows = db.execute(
        """SELECT p.name_fr, e.min_level, e.max_level, e.chance FROM encounter e
           JOIN pokemon p ON p.id = e.pokemon_id JOIN location l ON l.id = e.location_id
           WHERE l.identifier = 'route_1' AND e.version_id = ? AND e.method = 'WALK'
           ORDER BY p.name_fr""",
        (RED,),
    ).fetchall()
    # Roucool occupe les emplacements 0, 4, 5, 6, 8 et 9 : (51 + 25 + 25 + 13 + 11 + 3) / 256 = 50 %.
    assert rows == [("Rattata", 2, 4, 50.0), ("Roucool", 2, 5, 50.0)]


def test_version_exclusives(db):
    # Abo (23) est exclusif à Rouge, Sabelette (27) à Bleu ; aucun des deux n'est sauvage dans Jaune.
    assert any(method == "WALK" for _, method, *_ in encounters(db, 23, RED))
    assert not any(method == "WALK" for _, method, *_ in encounters(db, 23, BLUE))
    assert any(method == "WALK" for _, method, *_ in encounters(db, 27, BLUE))
    assert not any(method == "WALK" for _, method, *_ in encounters(db, 23, YELLOW))


def test_yellow_starters(db):
    gifts = {
        pokemon_id: location
        for pokemon_id, location in db.execute(
            """SELECT e.pokemon_id, l.identifier FROM encounter e JOIN location l ON l.id = e.location_id
               WHERE e.version_id = ? AND e.method = 'GIFT'""",
            (YELLOW,),
        )
    }
    assert gifts[25] == "oaks_lab"
    assert gifts[1] == "cerulean_trade_house"
    assert gifts[4] == "route_24"
    assert gifts[7] == "vermilion_city"


def test_legendaries_are_static(db):
    rows = db.execute(
        """SELECT e.pokemon_id, l.identifier, e.min_level FROM encounter e JOIN location l ON l.id = e.location_id
           WHERE e.method = 'STATIC' AND e.version_id = ? AND e.pokemon_id IN (144, 145, 146, 150)
           ORDER BY e.pokemon_id""",
        (RED,),
    ).fetchall()
    assert rows == [
        (144, "seafoam_islands_b4f", 50),
        (145, "power_plant", 50),
        (146, "victory_road_2f", 50),
        (150, "cerulean_cave_b1f", 70),
    ]


def test_pikachu_learnset_differs_in_yellow(db):
    def learnset(group):
        return db.execute(
            """SELECT level, move_id FROM pokemon_move
               WHERE pokemon_id = 25 AND version_group_id = ? AND method = 'LEVEL' ORDER BY level""",
            (group,),
        ).fetchall()

    assert learnset(1) != learnset(2)
    assert (9, 86) in learnset(1)  # Cage Éclair au niveau 9 dans Rouge/Bleu


def test_eevee_evolutions(db):
    rows = db.execute(
        """SELECT e.to_pokemon_id, e.method, i.identifier FROM evolution e
           LEFT JOIN item i ON i.id = e.item_id WHERE e.from_pokemon_id = 133 ORDER BY e.to_pokemon_id"""
    ).fetchall()
    assert rows == [(134, "ITEM", "water-stone"), (135, "ITEM", "thunder-stone"), (136, "ITEM", "fire-stone")]


def test_gen1_move_types(db):
    # En 1re génération, Morsure est de type Normal et Psyko a 90 de puissance.
    bite = db.execute("SELECT t.identifier FROM move m JOIN type t ON t.id = m.type_id WHERE m.id = 44").fetchone()
    assert bite == ("normal",)
    assert db.execute("SELECT power FROM move WHERE id = 94").fetchone() == (90,)


def test_every_encounter_location_has_a_french_name(db):
    missing = db.execute(
        """SELECT DISTINCT l.identifier FROM encounter e JOIN location l ON l.id = e.location_id
           WHERE trim(l.name_fr) = ''"""
    ).fetchall()
    assert missing == []
