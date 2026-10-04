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


# --- Cartes -----------------------------------------------------------------------


def test_world_map_contains_all_towns_and_routes(db):
    for version_group in (RED_BLUE, YELLOW_GROUP):
        world = db.execute(
            "SELECT id FROM map WHERE identifier = 'kanto' AND version_group_id = ?", (version_group,)
        ).fetchone()[0]
        children = scalar(db, "SELECT count(*) FROM map WHERE parent_map_id = ?", world)
        assert children == 11 + 25  # villes (dont le Plateau Indigo) et routes


def test_connected_maps_are_adjacent(db):
    """La Route 1 est juste au nord de Bourg Palette, centrée sur Jadielle."""
    rows = dict(
        (identifier, (x, y, w, h))
        for identifier, x, y, w, h in db.execute(
            "SELECT identifier, x, y, width, height FROM map WHERE version_group_id = ? AND parent_map_id IS NOT NULL",
            (RED_BLUE,),
        )
    )
    px, py, _, _ = rows["pallet-town"]
    rx, ry, _, rh = rows["route-1"]
    vx, vy, _, vh = rows["viridian-city"]
    assert (rx, ry + rh) == (px, py)
    assert vy + vh == ry and vx == rx - 5 * 32


def test_static_pokemon_on_maps(db):
    rows = set(
        db.execute(
            """SELECT m.identifier, p.name_fr, o.level FROM map_object o JOIN map m ON m.id = o.map_id
               JOIN pokemon p ON p.id = o.pokemon_id WHERE m.version_group_id = ?""",
            (RED_BLUE,),
        )
    )
    assert ("cerulean-cave-b1f", "Mewtwo", 70) in rows
    assert ("power-plant", "Électhor", 50) in rows


def test_map_items(db):
    # Pierre Lune de la Route 2 et CT du Mont Sélénite, objet caché de la Forêt de Jade.
    items = set(
        db.execute(
            """SELECT m.identifier, i.identifier, o.kind FROM map_object o JOIN map m ON m.id = o.map_id
               JOIN item i ON i.id = o.item_id WHERE m.version_group_id = ?""",
            (RED_BLUE,),
        )
    )
    assert ("route-2", "moon-stone", "item") in items
    assert ("mt-moon-1f", "tm12", "item") in items
    assert ("viridian-forest", "potion", "hidden_item") in items


def test_warps_lead_back(db):
    """La porte du Labo du Prof. Chen mène au labo, et sa sortie ramène devant la porte."""
    lab, pallet = (
        db.execute("SELECT id FROM map WHERE identifier = ? AND version_group_id = ?", (name, RED_BLUE)).fetchone()[0]
        for name in ("oaks-lab", "pallet-town")
    )
    entrance = db.execute("SELECT x, y, target_map_id FROM map_warp WHERE map_id = ?", (pallet,)).fetchall()
    assert any(target == lab for _, _, target in entrance)
    exits = db.execute("SELECT target_map_id, target_x, target_y FROM map_warp WHERE map_id = ?", (lab,)).fetchall()
    door = next((x, y) for x, y, target in entrance if target == lab)
    assert (pallet, *door) in exits


def test_tiles_exist_for_every_level(db, assets):
    rows = db.execute(
        """SELECT vg.identifier, m.identifier, m.level_count FROM map m
           JOIN version_group vg ON vg.id = m.version_group_id WHERE m.parent_map_id IS NULL"""
    ).fetchall()
    for version_group, identifier, levels in rows:
        folder = assets / "maps" / version_group / identifier
        for level in range(levels):
            assert any((folder / str(level)).glob("*.webp")), f"{folder}/{level}"
        # Le niveau 0 tient dans une seule tuile.
        assert [p.name for p in (folder / "0").iterdir()] == ["0_0.webp"]


def test_object_sprites_exist(db, assets):
    rows = db.execute(
        """SELECT DISTINCT vg.identifier, o.sprite FROM map_object o JOIN map m ON m.id = o.map_id
           JOIN version_group vg ON vg.id = m.version_group_id WHERE o.sprite IS NOT NULL"""
    ).fetchall()
    missing = [row for row in rows if not (assets / "maps" / row[0] / "sprites" / f"{row[1]}.png").exists()]
    assert missing == []


def _party(db, version_group, trainer_class):
    return db.execute(
        """SELECT p.name_fr, t.level, m1.name_fr, m2.name_fr, m3.name_fr, m4.name_fr FROM trainer_pokemon t
           JOIN map_object o ON o.id = t.map_object_id JOIN map m ON m.id = o.map_id
           JOIN pokemon p ON p.id = t.pokemon_id
           LEFT JOIN move m1 ON m1.id = t.move1_id LEFT JOIN move m2 ON m2.id = t.move2_id
           LEFT JOIN move m3 ON m3.id = t.move3_id LEFT JOIN move m4 ON m4.id = t.move4_id
           WHERE m.version_group_id = ? AND o.trainer_class = ? ORDER BY o.id, t.slot""",
        (version_group, trainer_class),
    ).fetchall()


def test_gym_leader_parties(db):
    # Rouge / Bleu : Onix de Pierre avec Patience (LoneMoves) ; Jaune : attaques de SpecialTrainerMoves.
    assert _party(db, RED_BLUE, "brock") == [
        ("Racaillou", 12, "Charge", "Boul’Armure", None, None),
        ("Onix", 14, "Charge", "Grincement", "Patience", None),
    ]
    assert _party(db, YELLOW_GROUP, "lt-surge") == [
        ("Raichu", 28, "Tonnerre", "Ultimapoing", "Ultimawashi", "Rugissement")
    ]


def test_trainer_default_moves(db):
    """Sans attaque spéciale, un Pokémon de dresseur connaît les 4 dernières attaques apprises à son niveau."""
    party = _party(db, RED_BLUE, "bug-catcher")
    assert ("Aspicot", 6, "Dard-Venin", "Sécrétion", None, None) in party
    assert ("Chenipan", 6, "Charge", "Sécrétion", None, None) in party
    # Seuls les rivaux (équipe selon le starter) n'ont pas d'équipe sur la carte.
    without = db.execute(
        """SELECT DISTINCT trainer_class FROM map_object WHERE kind = 'trainer'
           AND id NOT IN (SELECT map_object_id FROM trainer_pokemon)"""
    ).fetchall()
    assert {row[0] for row in without} <= {"rival1", "rival2", "rival3"}


def test_npc_offers(db):
    offers = set(
        db.execute(
            """SELECT m.identifier, n.kind, i.identifier, p.identifier, n.quantity, n.price, w.identifier
               FROM npc_offer n JOIN map_object o ON o.id = n.map_object_id JOIN map m ON m.id = o.map_id
               LEFT JOIN item i ON i.id = n.item_id LEFT JOIN pokemon p ON p.id = n.pokemon_id
               LEFT JOIN pokemon w ON w.id = n.wanted_pokemon_id WHERE m.version_group_id = ?""",
            (RED_BLUE,),
        )
    )
    assert ("route-1", "gift_item", "potion", None, 1, None, None) in offers
    assert ("viridian-mart", "sale", "poke-ball", None, None, 200, None) in offers
    assert ("celadon-mansion-roof-house", "gift_pokemon", None, "eevee", 25, None, None) in offers
    assert ("vermilion-trade-house", "trade", None, "farfetchd", None, None, "spearow") in offers
    assert ("pewter-gym", "gift_item", "tm34", None, 1, None, None) in offers  # CT Patience de Pierre


def test_pokemon_spots(db):
    spots = dict(
        db.execute(
            """SELECT m.identifier || '/' || s.kind, count(*) FROM map_spot s JOIN map m ON m.id = s.map_id
               WHERE m.version_group_id = ? GROUP BY m.identifier, s.kind""",
            (RED_BLUE,),
        )
    )
    assert spots["route-1/grass"] == 12
    assert spots["route-21/water"] == 12
    assert spots["mt-moon-1f/floor"] == 12
