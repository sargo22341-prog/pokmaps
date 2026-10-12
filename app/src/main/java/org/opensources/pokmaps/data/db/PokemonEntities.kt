package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Entités de la base pré-remplie pokedex.db, calquées sur tools/pokemaps_data/schema.sql
// (mêmes tables, colonnes, types, NOT NULL, clés primaires et index) : Room vérifie la correspondance
// à l'ouverture et PokedexSchemaTest la vérifie en CI. Les identifiants sont ceux de PokéAPI.

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
    @ColumnInfo(name = "description_fr") val descriptionFr: String?,
    @ColumnInfo(name = "hatch_counter") val hatchCounter: Int
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
    @ColumnInfo(name = "trade_species_id") val tradeSpeciesId: Int?,
    @ColumnInfo(name = "min_beauty") val minBeauty: Int?,
    @ColumnInfo(name = "relative_physical_stats") val relativePhysicalStats: Int?,
    @ColumnInfo(name = "personality_chance") val personalityChance: Int?
)
