-- Schéma de pokedex.db. Il doit rester identique aux entités Room de l'application
-- (noms de tables et colonnes, types, NOT NULL, clés primaires et index nommés index_<table>_<colonnes>).
-- Toute modification impose d'incrémenter SCHEMA_VERSION (builder.py) et la version de la base Room.
--
-- Les identifiants sont ceux de PokéAPI. Les données qui changent selon le jeu sont rattachées
-- à une génération (types, stats, table des types) ou à un groupe de versions (attaques apprises,
-- caractéristiques des attaques, CT/CS, évolutions).

CREATE TABLE generation (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

CREATE TABLE region (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

CREATE TABLE version_group (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    generation_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL,
    -- Dossier des sprites du jeu dans les assets : sprites/pokemon/<identifier>/<pokemon_id>.png
    has_sprites INTEGER NOT NULL
);

CREATE TABLE version (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    version_group_id INTEGER NOT NULL
);
CREATE INDEX index_version_version_group_id ON version (version_group_id);

CREATE TABLE pokedex (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    region_id INTEGER
);

CREATE TABLE version_group_pokedex (
    version_group_id INTEGER NOT NULL,
    pokedex_id INTEGER NOT NULL,
    PRIMARY KEY (version_group_id, pokedex_id)
);

CREATE TABLE pokedex_entry (
    pokedex_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    number INTEGER NOT NULL,
    PRIMARY KEY (pokedex_id, pokemon_id)
);
CREATE INDEX index_pokedex_entry_pokemon_id ON pokedex_entry (pokemon_id);

CREATE TABLE type (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    generation_id INTEGER NOT NULL
);

-- Multiplicateur de dégâts en pourcentage (0, 50, 100, 200) pour chaque génération.
CREATE TABLE type_efficacy (
    generation_id INTEGER NOT NULL,
    attacking_type_id INTEGER NOT NULL,
    defending_type_id INTEGER NOT NULL,
    damage_factor INTEGER NOT NULL,
    PRIMARY KEY (generation_id, attacking_type_id, defending_type_id)
);

CREATE TABLE stat (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

CREATE TABLE growth_rate (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

-- Une ligne par espèce (forme par défaut).
CREATE TABLE pokemon (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    name_en TEXT NOT NULL,
    genus_fr TEXT NOT NULL,
    generation_id INTEGER NOT NULL,
    evolves_from_id INTEGER,
    evolution_chain_id INTEGER NOT NULL,
    capture_rate INTEGER NOT NULL,
    -- Proportion de femelles en huitièmes, -1 si asexué.
    gender_rate INTEGER NOT NULL,
    growth_rate_id INTEGER NOT NULL,
    height_dm INTEGER NOT NULL,
    weight_hg INTEGER NOT NULL,
    is_legendary INTEGER NOT NULL,
    is_mythical INTEGER NOT NULL,
    is_baby INTEGER NOT NULL,
    description_fr TEXT
);
CREATE INDEX index_pokemon_evolution_chain_id ON pokemon (evolution_chain_id);

CREATE TABLE pokemon_type (
    pokemon_id INTEGER NOT NULL,
    generation_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, generation_id, slot)
);
CREATE INDEX index_pokemon_type_type_id ON pokemon_type (type_id);

-- En 1re génération : PV, Attaque, Défense, Vitesse et Spécial (stat 9).
CREATE TABLE pokemon_stat (
    pokemon_id INTEGER NOT NULL,
    generation_id INTEGER NOT NULL,
    stat_id INTEGER NOT NULL,
    base_stat INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, generation_id, stat_id)
);

CREATE TABLE move (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    generation_id INTEGER NOT NULL
);

-- Caractéristiques d'une attaque dans un jeu donné (elles ont changé au fil des générations).
-- damage_class : physical, special ou status (jusqu'à la 3e génération, elle dépend du type).
CREATE TABLE move_version_group (
    move_id INTEGER NOT NULL,
    version_group_id INTEGER NOT NULL,
    type_id INTEGER NOT NULL,
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER NOT NULL,
    damage_class TEXT NOT NULL,
    PRIMARY KEY (move_id, version_group_id)
);

CREATE TABLE item (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    category TEXT NOT NULL,
    -- Icône dans les assets : sprites/items/<identifier>.png
    has_sprite INTEGER NOT NULL
);

-- CT / CS d'un jeu (item = CT01, CS01…).
CREATE TABLE machine (
    version_group_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    move_id INTEGER NOT NULL,
    PRIMARY KEY (version_group_id, item_id)
);
CREATE INDEX index_machine_move_id ON machine (move_id);

-- method : identifiant PokéAPI (level-up, machine, egg, tutor…). level = 0 hors level-up.
CREATE TABLE pokemon_move (
    pokemon_id INTEGER NOT NULL,
    version_group_id INTEGER NOT NULL,
    move_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    level INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, version_group_id, move_id, method, level)
);
CREATE INDEX index_pokemon_move_move_id ON pokemon_move (move_id);

-- trigger : identifiant PokéAPI (level-up, use-item, trade…). Conditions NULL si non requises.
CREATE TABLE evolution (
    id INTEGER NOT NULL PRIMARY KEY,
    version_group_id INTEGER NOT NULL,
    from_pokemon_id INTEGER NOT NULL,
    to_pokemon_id INTEGER NOT NULL,
    trigger TEXT NOT NULL,
    min_level INTEGER,
    item_id INTEGER,
    held_item_id INTEGER,
    min_happiness INTEGER,
    time_of_day TEXT,
    known_move_id INTEGER,
    trade_species_id INTEGER
);
CREATE INDEX index_evolution_from_pokemon_id ON evolution (from_pokemon_id);
CREATE INDEX index_evolution_to_pokemon_id ON evolution (to_pokemon_id);

CREATE TABLE location (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    region_id INTEGER
);

-- Zone d'un lieu (étage d'une grotte, partie d'une route…) : c'est à ce niveau que sont les rencontres.
CREATE TABLE location_area (
    id INTEGER NOT NULL PRIMARY KEY,
    location_id INTEGER NOT NULL,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);
CREATE INDEX index_location_area_location_id ON location_area (location_id);

CREATE TABLE encounter_method (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    -- 1 : don, Pokémon fixe ou échange (pas de probabilité).
    is_one_off INTEGER NOT NULL
);

CREATE TABLE encounter_condition_value (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

-- Rencontres regroupées par (version, zone, Pokémon, méthode, conditions).
-- chance : probabilité (%) que la rencontre soit ce Pokémon, NULL pour les rencontres uniques.
-- quantity : nombre de rencontres uniques (ex. 6 Voltorbe à la Centrale), 1 sinon.
CREATE TABLE encounter (
    id INTEGER NOT NULL PRIMARY KEY,
    version_id INTEGER NOT NULL,
    location_area_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    method_id INTEGER NOT NULL,
    min_level INTEGER NOT NULL,
    max_level INTEGER NOT NULL,
    chance REAL,
    quantity INTEGER NOT NULL,
    note_fr TEXT
);
CREATE INDEX index_encounter_pokemon_id ON encounter (pokemon_id);
CREATE INDEX index_encounter_location_area_id ON encounter (location_area_id);
CREATE INDEX index_encounter_version_id ON encounter (version_id);

-- Conditions d'une rencontre (moment de la journée, saison…) : aucune en 1re génération.
CREATE TABLE encounter_condition (
    encounter_id INTEGER NOT NULL,
    condition_value_id INTEGER NOT NULL,
    PRIMARY KEY (encounter_id, condition_value_id)
);

-- Taux de rencontre d'une zone par méthode (sur 256 en 1re génération).
CREATE TABLE encounter_rate (
    version_id INTEGER NOT NULL,
    location_area_id INTEGER NOT NULL,
    method_id INTEGER NOT NULL,
    rate INTEGER NOT NULL,
    PRIMARY KEY (version_id, location_area_id, method_id)
);
