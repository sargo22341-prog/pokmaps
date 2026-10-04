package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Entités de la base pré-remplie pokedex.db, calquées sur tools/pokemaps_data/schema.sql
// (mêmes tables, colonnes, types, NOT NULL, clés primaires et index) : Room vérifie la correspondance
// à l'ouverture et PokedexSchemaTest la vérifie en CI. Les identifiants sont ceux de PokéAPI.

@Entity(
    tableName = "generation"
)
data class GenerationEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "region"
)
data class RegionEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "version_group"
)
data class VersionGroupEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "generation_id") val generationId: Int,
    @ColumnInfo(name = "sort_order") val sortOrder: Int,
    @ColumnInfo(name = "has_sprites") val hasSprites: Boolean
)

@Entity(
    tableName = "version",
    indices = [
        Index("version_group_id", name = "index_version_version_group_id")
    ]
)
data class VersionEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int
)

@Entity(
    tableName = "pokedex"
)
data class PokedexEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "region_id") val regionId: Int?
)

@Entity(
    tableName = "version_group_pokedex",
    primaryKeys = ["version_group_id", "pokedex_id"]
)
data class VersionGroupPokedexEntity(
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "pokedex_id") val pokedexId: Int
)

@Entity(
    tableName = "pokedex_entry",
    primaryKeys = ["pokedex_id", "pokemon_id"],
    indices = [
        Index("pokemon_id", name = "index_pokedex_entry_pokemon_id")
    ]
)
data class PokedexEntryEntity(
    @ColumnInfo(name = "pokedex_id") val pokedexId: Int,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    val number: Int
)

@Entity(
    tableName = "type"
)
data class TypeEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "generation_id") val generationId: Int
)

@Entity(
    tableName = "type_efficacy",
    primaryKeys = ["generation_id", "attacking_type_id", "defending_type_id"]
)
data class TypeEfficacyEntity(
    @ColumnInfo(name = "generation_id") val generationId: Int,
    @ColumnInfo(name = "attacking_type_id") val attackingTypeId: Int,
    @ColumnInfo(name = "defending_type_id") val defendingTypeId: Int,
    @ColumnInfo(name = "damage_factor") val damageFactor: Int
)

@Entity(
    tableName = "stat"
)
data class StatEntity(@PrimaryKey val id: Int, val identifier: String, @ColumnInfo(name = "name_fr") val nameFr: String)

@Entity(
    tableName = "growth_rate"
)
data class GrowthRateEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "pokemon",
    indices = [
        Index("evolution_chain_id", name = "index_pokemon_evolution_chain_id")
    ]
)
data class PokemonEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "name_en") val nameEn: String,
    @ColumnInfo(name = "genus_fr") val genusFr: String,
    @ColumnInfo(name = "generation_id") val generationId: Int,
    @ColumnInfo(name = "evolves_from_id") val evolvesFromId: Int?,
    @ColumnInfo(name = "evolution_chain_id") val evolutionChainId: Int,
    @ColumnInfo(name = "capture_rate") val captureRate: Int,
    @ColumnInfo(name = "gender_rate") val genderRate: Int,
    @ColumnInfo(name = "growth_rate_id") val growthRateId: Int,
    @ColumnInfo(name = "height_dm") val heightDm: Int,
    @ColumnInfo(name = "weight_hg") val weightHg: Int,
    @ColumnInfo(name = "is_legendary") val isLegendary: Boolean,
    @ColumnInfo(name = "is_mythical") val isMythical: Boolean,
    @ColumnInfo(name = "is_baby") val isBaby: Boolean,
    @ColumnInfo(name = "description_fr") val descriptionFr: String?
)

@Entity(
    tableName = "pokemon_type",
    primaryKeys = ["pokemon_id", "generation_id", "slot"],
    indices = [
        Index("type_id", name = "index_pokemon_type_type_id")
    ]
)
data class PokemonTypeEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "generation_id") val generationId: Int,
    val slot: Int,
    @ColumnInfo(name = "type_id") val typeId: Int
)

@Entity(
    tableName = "pokemon_stat",
    primaryKeys = ["pokemon_id", "generation_id", "stat_id"]
)
data class PokemonStatEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "generation_id") val generationId: Int,
    @ColumnInfo(name = "stat_id") val statId: Int,
    @ColumnInfo(name = "base_stat") val baseStat: Int
)

@Entity(
    tableName = "move"
)
data class MoveEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "generation_id") val generationId: Int
)

@Entity(
    tableName = "move_version_group",
    primaryKeys = ["move_id", "version_group_id"]
)
data class MoveVersionGroupEntity(
    @ColumnInfo(name = "move_id") val moveId: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "type_id") val typeId: Int,
    val power: Int?,
    val accuracy: Int?,
    val pp: Int,
    @ColumnInfo(name = "damage_class") val damageClass: String
)

@Entity(
    tableName = "item"
)
data class ItemEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    val category: String,
    @ColumnInfo(name = "has_sprite") val hasSprite: Boolean
)

@Entity(
    tableName = "machine",
    primaryKeys = ["version_group_id", "item_id"],
    indices = [
        Index("move_id", name = "index_machine_move_id")
    ]
)
data class MachineEntity(
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "item_id") val itemId: Int,
    @ColumnInfo(name = "move_id") val moveId: Int
)

@Entity(
    tableName = "pokemon_move",
    primaryKeys = ["pokemon_id", "version_group_id", "move_id", "method", "level"],
    indices = [
        Index("move_id", name = "index_pokemon_move_move_id")
    ]
)
data class PokemonMoveEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "move_id") val moveId: Int,
    val method: String,
    val level: Int
)

@Entity(
    tableName = "evolution",
    indices = [
        Index("from_pokemon_id", name = "index_evolution_from_pokemon_id"),
        Index("to_pokemon_id", name = "index_evolution_to_pokemon_id")
    ]
)
data class EvolutionEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "from_pokemon_id") val fromPokemonId: Int,
    @ColumnInfo(name = "to_pokemon_id") val toPokemonId: Int,
    val trigger: String,
    @ColumnInfo(name = "min_level") val minLevel: Int?,
    @ColumnInfo(name = "item_id") val itemId: Int?,
    @ColumnInfo(name = "held_item_id") val heldItemId: Int?,
    @ColumnInfo(name = "min_happiness") val minHappiness: Int?,
    @ColumnInfo(name = "time_of_day") val timeOfDay: String?,
    @ColumnInfo(name = "known_move_id") val knownMoveId: Int?,
    @ColumnInfo(name = "trade_species_id") val tradeSpeciesId: Int?
)

@Entity(
    tableName = "location"
)
data class LocationEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "region_id") val regionId: Int?
)

@Entity(
    tableName = "location_area",
    indices = [
        Index("location_id", name = "index_location_area_location_id")
    ]
)
data class LocationAreaEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "location_id") val locationId: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "encounter_method"
)
data class EncounterMethodEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "sort_order") val sortOrder: Int,
    @ColumnInfo(name = "is_one_off") val isOneOff: Boolean
)

@Entity(
    tableName = "encounter_condition_value"
)
data class EncounterConditionValueEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "encounter",
    indices = [
        Index("pokemon_id", name = "index_encounter_pokemon_id"),
        Index("location_area_id", name = "index_encounter_location_area_id"),
        Index("version_id", name = "index_encounter_version_id")
    ]
)
data class EncounterEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "version_id") val versionId: Int,
    @ColumnInfo(name = "location_area_id") val locationAreaId: Int,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "method_id") val methodId: Int,
    @ColumnInfo(name = "min_level") val minLevel: Int,
    @ColumnInfo(name = "max_level") val maxLevel: Int,
    val chance: Double?,
    val quantity: Int,
    @ColumnInfo(name = "note_fr") val noteFr: String?
)

@Entity(
    tableName = "encounter_condition",
    primaryKeys = ["encounter_id", "condition_value_id"]
)
data class EncounterConditionEntity(
    @ColumnInfo(name = "encounter_id") val encounterId: Int,
    @ColumnInfo(name = "condition_value_id") val conditionValueId: Int
)

@Entity(
    tableName = "encounter_rate",
    primaryKeys = ["version_id", "location_area_id", "method_id"]
)
data class EncounterRateEntity(
    @ColumnInfo(name = "version_id") val versionId: Int,
    @ColumnInfo(name = "location_area_id") val locationAreaId: Int,
    @ColumnInfo(name = "method_id") val methodId: Int,
    val rate: Int
)

@Entity(
    tableName = "map",
    indices = [
        Index("version_group_id", name = "index_map_version_group_id"),
        Index("parent_map_id", name = "index_map_parent_map_id")
    ]
)
data class MapEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "parent_map_id") val parentMapId: Int?,
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
    @ColumnInfo(name = "level_count") val levelCount: Int
)

@Entity(
    tableName = "map_area",
    primaryKeys = ["map_id", "location_area_id"],
    indices = [
        Index("location_area_id", name = "index_map_area_location_area_id")
    ]
)
data class MapAreaEntity(
    @ColumnInfo(name = "map_id") val mapId: Int,
    @ColumnInfo(name = "location_area_id") val locationAreaId: Int
)

@Entity(
    tableName = "map_warp",
    indices = [
        Index("map_id", name = "index_map_warp_map_id")
    ]
)
data class MapWarpEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "map_id") val mapId: Int,
    val x: Int,
    val y: Int,
    @ColumnInfo(name = "target_map_id") val targetMapId: Int?,
    @ColumnInfo(name = "target_x") val targetX: Int?,
    @ColumnInfo(name = "target_y") val targetY: Int?
)

@Entity(
    tableName = "map_object",
    indices = [
        Index("map_id", name = "index_map_object_map_id"),
        Index("item_id", name = "index_map_object_item_id"),
        Index("pokemon_id", name = "index_map_object_pokemon_id")
    ]
)
data class MapObjectEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "map_id") val mapId: Int,
    val kind: String,
    val x: Int,
    val y: Int,
    val sprite: String?,
    @ColumnInfo(name = "item_id") val itemId: Int?,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int?,
    val level: Int?,
    @ColumnInfo(name = "trainer_class") val trainerClass: String?
)
