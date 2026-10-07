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
    sort_order INTEGER NOT NULL
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
    -- Icône dans les assets : sprites/items/<identifier>.webp
    has_sprite INTEGER NOT NULL,
    -- Description du Pokédex des objets (NULL pour les CT / CS : c'est l'attaque qui compte).
    description_fr TEXT
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

-- Cartes générées depuis les désassemblages pret, une série par groupe de versions.
-- Une carte affichable (parent_map_id NULL) a ses tuiles dans les assets :
--   maps/<version_group.identifier>/<map.identifier>/<niveau>/<ligne>_<colonne>.webp
-- tuiles de 256 px, niveaux 0 à level_count - 1, le dernier à la taille réelle (1 px = 1 pixel Game Boy).
-- Les villes et routes sont des parties de la carte du monde (« kanto ») : parent_map_id la désigne,
-- (x, y, width, height) est leur rectangle dans cette carte et level_count vaut 0.
-- Toutes les coordonnées (x, y) sont en pixels de la carte affichée.
CREATE TABLE map (
    id INTEGER NOT NULL PRIMARY KEY,
    version_group_id INTEGER NOT NULL,
    identifier TEXT NOT NULL,
    name_fr TEXT NOT NULL,
    parent_map_id INTEGER,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    level_count INTEGER NOT NULL
);
CREATE INDEX index_map_version_group_id ON map (version_group_id);
CREATE INDEX index_map_parent_map_id ON map (parent_map_id);

-- Zones PokéAPI (et donc rencontres) de chaque carte.
CREATE TABLE map_area (
    map_id INTEGER NOT NULL,
    location_area_id INTEGER NOT NULL,
    PRIMARY KEY (map_id, location_area_id)
);
CREATE INDEX index_map_area_location_area_id ON map_area (location_area_id);

-- Warps (portes, escaliers, entrées de grottes) : position et arrivée (NULL si inconnue).
CREATE TABLE map_warp (
    id INTEGER NOT NULL PRIMARY KEY,
    map_id INTEGER NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    target_map_id INTEGER,
    target_x INTEGER,
    target_y INTEGER
);
CREATE INDEX index_map_warp_map_id ON map_warp (map_id);

-- Objets et personnages d'une carte. kind : item (objet ramassable), hidden_item (objet caché),
-- trainer (dresseur, trainer_class = classe pret, ex. youngster), pokemon (Pokémon fixe, avec son niveau),
-- personnage : npc (une personne), npc_object (objet du décor qui parle ou donne : Fossile, Poké Ball, rocher…) ou
-- npc_pokemon (Pokémon qui n'est pas à combattre), ou une installation sans sprite : vending_machine (distributeur)
-- ou prize_vendor (comptoir des lots du Casino).
-- sprite : image dans les assets, maps/<version_group.identifier>/sprites/<sprite>.webp.
-- name_fr : nom affiché (classe du dresseur, personnage d'après son sprite, Pokémon, objet ou installation).
CREATE TABLE map_object (
    id INTEGER NOT NULL PRIMARY KEY,
    map_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL,
    sprite TEXT,
    item_id INTEGER,
    pokemon_id INTEGER,
    level INTEGER,
    trainer_class TEXT,
    name_fr TEXT NOT NULL
);
CREATE INDEX index_map_object_map_id ON map_object (map_id);
CREATE INDEX index_map_object_item_id ON map_object (item_id);
CREATE INDEX index_map_object_pokemon_id ON map_object (pokemon_id);

-- Équipe d'un dresseur de la carte (map_object de type trainer), avec les attaques qu'il utilise :
-- les 4 dernières apprises au niveau du Pokémon, plus les attaques spéciales des champions et du Conseil 4.
CREATE TABLE trainer_pokemon (
    map_object_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,
    pokemon_id INTEGER NOT NULL,
    level INTEGER NOT NULL,
    move1_id INTEGER,
    move2_id INTEGER,
    move3_id INTEGER,
    move4_id INTEGER,
    PRIMARY KEY (map_object_id, slot)
);

-- Ce que propose un personnage ou une installation (map_object) quand on lui parle. kind :
--   gift_item (objet donné, quantity), gift_pokemon (Pokémon donné, quantity = niveau), sale (objet vendu, price),
--   trade (pokemon_id reçu contre wanted_pokemon_id), exchange (item_id reçu contre wanted_item_id),
--   prize_item et prize_pokemon (lot du Casino, price en jetons, quantity = niveau du Pokémon),
--   coin_sale (quantity jetons pour price ¥), coin_gift (quantity jetons donnés),
--   fossil (fossile item_id ranimé en pokemon_id, quantity = niveau),
--   heal, cable_club, name_rater, daycare (services : soins, Club Link, Mme Notation, pension).
-- version_id : version où l'offre existe (lots du Casino de Rouge ou de Bleu), NULL pour toutes celles du jeu.
CREATE TABLE npc_offer (
    id INTEGER NOT NULL PRIMARY KEY,
    map_object_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    item_id INTEGER,
    pokemon_id INTEGER,
    quantity INTEGER,
    price INTEGER,
    wanted_pokemon_id INTEGER,
    wanted_item_id INTEGER,
    version_id INTEGER
);
CREATE INDEX index_npc_offer_map_object_id ON npc_offer (map_object_id);

-- Emplacements où dessiner les Pokémon sauvages d'une carte (ville, route ou carte intérieure), bien répartis :
-- kind grass (hautes herbes), water (eau : surf et pêche) ou floor (sol des grottes et bâtiments).
CREATE TABLE map_spot (
    id INTEGER NOT NULL PRIMARY KEY,
    map_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    x INTEGER NOT NULL,
    y INTEGER NOT NULL
);
CREATE INDEX index_map_spot_map_id ON map_spot (map_id);
