-- Schéma de pokedex.db. Il doit rester identique aux entités Room de l'application
-- (noms de tables et colonnes, types, NOT NULL, clés primaires et index nommés index_<table>_<colonnes>).
-- Toute modification impose d'incrémenter SCHEMA_VERSION (builder.py) et la version de la base Room.

CREATE TABLE version_group (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

CREATE TABLE version (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    version_group_id INTEGER NOT NULL
);

CREATE TABLE type (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    -- En 1re génération, la catégorie (physique / spéciale) dépend du type de l'attaque.
    is_special INTEGER NOT NULL
);

CREATE TABLE item (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL
);

CREATE TABLE pokemon (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    name_en TEXT NOT NULL,
    genus_fr TEXT NOT NULL,
    type1_id INTEGER NOT NULL,
    type2_id INTEGER,
    base_hp INTEGER NOT NULL,
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_speed INTEGER NOT NULL,
    base_special INTEGER NOT NULL,
    base_exp INTEGER NOT NULL,
    growth_rate TEXT NOT NULL,
    height_dm INTEGER NOT NULL,
    weight_hg INTEGER NOT NULL,
    description_fr TEXT
);

-- Données qui varient entre Rouge/Bleu et Jaune.
CREATE TABLE pokemon_version_group (
    pokemon_id INTEGER NOT NULL,
    version_group_id INTEGER NOT NULL,
    catch_rate INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, version_group_id)
);

CREATE TABLE move (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    type_id INTEGER NOT NULL,
    power INTEGER NOT NULL,
    accuracy INTEGER NOT NULL,
    pp INTEGER NOT NULL,
    effect TEXT NOT NULL
);

CREATE TABLE machine (
    id INTEGER NOT NULL PRIMARY KEY,
    is_hm INTEGER NOT NULL,
    number INTEGER NOT NULL,
    move_id INTEGER NOT NULL
);

-- method : START (connue au niveau 1), LEVEL (apprise au niveau `level`), MACHINE (CT/CS, level = 0).
CREATE TABLE pokemon_move (
    pokemon_id INTEGER NOT NULL,
    version_group_id INTEGER NOT NULL,
    move_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    level INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, version_group_id, move_id, method, level)
);
CREATE INDEX index_pokemon_move_move_id ON pokemon_move (move_id);

-- method : LEVEL (min_level), ITEM (item_id), TRADE.
CREATE TABLE evolution (
    from_pokemon_id INTEGER NOT NULL,
    to_pokemon_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    min_level INTEGER,
    item_id INTEGER,
    PRIMARY KEY (from_pokemon_id, to_pokemon_id)
);
CREATE INDEX index_evolution_to_pokemon_id ON evolution (to_pokemon_id);

-- id = numéro de la carte dans le jeu (constante pret).
CREATE TABLE location (
    id INTEGER NOT NULL PRIMARY KEY,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    area_identifier TEXT NOT NULL,
    area_name_fr TEXT NOT NULL,
    kind TEXT NOT NULL
);
CREATE INDEX index_location_area_identifier ON location (area_identifier);

-- method : WALK, SURF, OLD_ROD, GOOD_ROD, SUPER_ROD, STATIC, GIFT, TRADE, PRIZE, PURCHASE, FOSSIL.
-- chance : probabilité (%) que la rencontre soit ce Pokémon, NULL pour les rencontres uniques.
CREATE TABLE encounter (
    id INTEGER NOT NULL PRIMARY KEY,
    version_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    min_level INTEGER,
    max_level INTEGER,
    chance REAL,
    note_fr TEXT
);
CREATE INDEX index_encounter_pokemon_id ON encounter (pokemon_id);
CREATE INDEX index_encounter_location_id ON encounter (location_id);

-- Taux de rencontre par pas (sur 256) dans les herbes / grottes (WALK) et sur l'eau (SURF).
CREATE TABLE encounter_rate (
    version_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    method TEXT NOT NULL,
    rate INTEGER NOT NULL,
    PRIMARY KEY (version_id, location_id, method)
);
