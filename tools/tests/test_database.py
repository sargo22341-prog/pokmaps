"""Contrôles de la base générée à partir des vraies sources (CSV PokéAPI + tools/data/)."""

from pokemaps_data.builder import SCHEMA_VERSION
from pokemaps_data.validate import validate

RED, BLUE, YELLOW = 1, 2, 3
RED_BLUE, YELLOW_GROUP = 1, 2
GEN1 = 1


def scalar(db, query, *args):
    return db.execute(query, args).fetchone()[0]


def test_validation_passes(database):
    assert validate(database) == []


def test_schema_version(db):
    assert scalar(db, "PRAGMA user_version") == SCHEMA_VERSION


def test_kanto_pokedex(db):
    assert (
        scalar(
            db,
            "SELECT count(*) FROM pokedex_entry pe JOIN pokedex p ON p.id = pe.pokedex_id WHERE p.identifier = 'kanto'",
        )
        == 151
    )
    assert scalar(db, "SELECT count(*) FROM pokemon") == 151


def test_french_names(db):
    names = dict(db.execute("SELECT id, name_fr FROM pokemon WHERE id IN (1, 25, 122, 133)"))
    assert names == {1: "Bulbizarre", 25: "Pikachu", 122: "M. Mime", 133: "Évoli"}
    assert dict(db.execute("SELECT id, name_fr FROM version")) == {RED: "Rouge", BLUE: "Bleu", YELLOW: "Jaune"}


def test_gen1_special_stat(db):
    stats = dict(
        db.execute("SELECT stat_id, base_stat FROM pokemon_stat WHERE pokemon_id = 65 AND generation_id = ?", (GEN1,))
    )
    # Alakazam : PV, Attaque, Défense, Vitesse, Spécial.
    assert stats == {1: 55, 2: 50, 3: 45, 6: 120, 9: 135}


def test_gen1_types(db):
    def types(pokemon_id):
        return [
            row[0]
            for row in db.execute(
                """SELECT t.identifier FROM pokemon_type pt JOIN type t ON t.id = pt.type_id
                   WHERE pt.pokemon_id = ? AND pt.generation_id = ? ORDER BY pt.slot""",
                (pokemon_id, GEN1),
            )
        ]

    assert types(35) == ["normal"]  # Mélofée, Fée seulement depuis la 6e génération
    assert types(81) == ["electric"]  # Magnéti, Acier depuis la 2e génération
    assert scalar(db, "SELECT count(*) FROM type") == 15


def test_gen1_type_chart(db):
    def factor(attacking, defending):
        return scalar(
            db,
            """SELECT damage_factor FROM type_efficacy e JOIN type a ON a.id = e.attacking_type_id
               JOIN type d ON d.id = e.defending_type_id
               WHERE e.generation_id = ? AND a.identifier = ? AND d.identifier = ?""",
            GEN1,
            attacking,
            defending,
        )

    assert factor("ghost", "psychic") == 0  # bug célèbre de la 1re génération
    assert factor("bug", "poison") == 200
    assert factor("ice", "fire") == 100


def test_gen1_moves(db):
    def move(move_id):
        return db.execute(
            """SELECT t.identifier, mvg.power, mvg.damage_class FROM move_version_group mvg
               JOIN type t ON t.id = mvg.type_id WHERE mvg.move_id = ? AND mvg.version_group_id = ?""",
            (move_id, RED_BLUE),
        ).fetchone()

    assert move(44) == ("normal", 60, "physical")  # Morsure : Normal avant la 2e génération
    assert move(16) == ("normal", 40, "physical")  # Tornade
    assert move(57) == ("water", 95, "special")  # Surf


def test_route_1_red(db):
    rows = db.execute(
        """SELECT p.name_fr, e.min_level, e.max_level, e.chance FROM encounter e
           JOIN pokemon p ON p.id = e.pokemon_id JOIN location_area a ON a.id = e.location_area_id
           JOIN location l ON l.id = a.location_id JOIN encounter_method m ON m.id = e.method_id
           WHERE l.identifier = 'kanto-route-1' AND e.version_id = ? AND m.identifier = 'walk'
           ORDER BY p.name_fr""",
        (RED,),
    ).fetchall()
    assert rows == [("Rattata", 2, 4, 50.0), ("Roucool", 2, 5, 50.0)]


def test_version_exclusives(db):
    def walk_versions(pokemon_id):
        return {
            row[0]
            for row in db.execute(
                """SELECT e.version_id FROM encounter e JOIN encounter_method m ON m.id = e.method_id
                   WHERE e.pokemon_id = ? AND m.identifier = 'walk'""",
                (pokemon_id,),
            )
        }

    assert walk_versions(23) == {RED}  # Abo
    assert walk_versions(27) == {BLUE, YELLOW}  # Sabelette


def test_one_off_encounters(db):
    rows = db.execute(
        """SELECT a.identifier, m.identifier, e.quantity, e.note_fr FROM encounter e
           JOIN location_area a ON a.id = e.location_area_id JOIN encounter_method m ON m.id = e.method_id
           WHERE e.version_id = ? AND e.pokemon_id = 100""",
        (RED,),
    ).fetchall()
    assert ("", "static", 6, "Déguisé en Poké Ball") in rows


def test_curation(db):
    # Le doublon du Magicarpe vendu « Route 3 » est retiré, celui de la Route 4 annoté.
    magikarp = db.execute(
        """SELECT l.identifier, e.note_fr FROM encounter e JOIN encounter_method m ON m.id = e.method_id
           JOIN location_area a ON a.id = e.location_area_id JOIN location l ON l.id = a.location_id
           WHERE e.pokemon_id = 129 AND m.identifier = 'gift' AND e.version_id = ?""",
        (RED,),
    ).fetchall()
    assert magikarp == [("kanto-route-4", "Vendu 500 ₽ par un marchand (une seule fois)")]
    trade = scalar(db, "SELECT note_fr FROM encounter WHERE pokemon_id = 122 AND version_id = ?", YELLOW)
    assert trade == "Échange contre Mélofée"
    assert scalar(db, "SELECT name_fr FROM location WHERE identifier = 'seafoam-islands'") == "Îles Écume"


def test_fossils_have_conditions(db):
    conditions = {
        row[0]
        for row in db.execute(
            """SELECT v.identifier FROM encounter_condition c
               JOIN encounter_condition_value v ON v.id = c.condition_value_id
               JOIN encounter e ON e.id = c.encounter_id WHERE e.pokemon_id = 138"""
        )
    }
    assert conditions == {"item-helix-fossil"}


def test_learnsets_differ_between_red_blue_and_yellow(db):
    def learnset(group):
        return db.execute(
            """SELECT level, move_id FROM pokemon_move
               WHERE pokemon_id = 25 AND version_group_id = ? AND method = 'level-up' ORDER BY level, move_id""",
            (group,),
        ).fetchall()

    assert learnset(RED_BLUE) != learnset(YELLOW_GROUP)
    assert (9, 86) in learnset(RED_BLUE)  # Cage Éclair au niveau 9


def test_gen1_evolutions(db):
    eevee = db.execute(
        """SELECT e.to_pokemon_id, e.trigger, i.identifier FROM evolution e LEFT JOIN item i ON i.id = e.item_id
           WHERE e.from_pokemon_id = 133 AND e.version_group_id = ? ORDER BY e.to_pokemon_id""",
        (RED_BLUE,),
    ).fetchall()
    # Mentali et Noctali (2e génération) ne sont pas proposés.
    assert eevee == [
        (134, "use-item", "water-stone"),
        (135, "use-item", "thunder-stone"),
        (136, "use-item", "fire-stone"),
    ]


def test_sprites(assets, db):
    sprites = assets / "sprites"
    for pokemon_id in (1, 25, 151):
        assert (sprites / "pokemon/icon" / f"{pokemon_id}.png").is_file()
        assert (sprites / "pokemon/red-blue" / f"{pokemon_id}.png").is_file()
        assert (sprites / "pokemon/yellow" / f"{pokemon_id}.png").is_file()
    missing = [
        identifier
        for identifier, has_sprite in db.execute("SELECT identifier, has_sprite FROM item")
        if has_sprite != (sprites / "items" / f"{identifier}.png").is_file()
    ]
    assert missing == []
    assert scalar(db, "SELECT count(*) FROM item WHERE has_sprite = 0") == 0
