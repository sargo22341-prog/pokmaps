package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

// Objets tenus et œufs dès la 2e génération, talents dès la 3e : ces entités suivent
// tools/pokemaps_data/schema.sql comme Entities.kt.

@Entity(
    tableName = "pokemon_item",
    primaryKeys = ["pokemon_id", "version_id", "item_id"]
)
data class PokemonItemEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "version_id") val versionId: Int,
    @ColumnInfo(name = "item_id") val itemId: Int,
    val rarity: Int
)

@Entity(
    tableName = "egg_group"
)
data class EggGroupEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String
)

@Entity(
    tableName = "pokemon_egg_group",
    primaryKeys = ["pokemon_id", "egg_group_id"]
)
data class PokemonEggGroupEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "egg_group_id") val eggGroupId: Int
)

@Entity(
    tableName = "ability"
)
data class AbilityEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    @ColumnInfo(name = "generation_id") val generationId: Int
)

@Entity(
    tableName = "ability_version_group",
    primaryKeys = ["ability_id", "version_group_id"]
)
data class AbilityVersionGroupEntity(
    @ColumnInfo(name = "ability_id") val abilityId: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "description_fr") val descriptionFr: String?
)

@Entity(
    tableName = "pokemon_ability",
    primaryKeys = ["pokemon_id", "generation_id", "slot"]
)
data class PokemonAbilityEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "generation_id") val generationId: Int,
    val slot: Int,
    @ColumnInfo(name = "ability_id") val abilityId: Int,
    @ColumnInfo(name = "is_hidden") val isHidden: Boolean
)
