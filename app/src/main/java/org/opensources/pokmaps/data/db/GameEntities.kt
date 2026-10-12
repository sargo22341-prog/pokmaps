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
    @ColumnInfo(name = "remake_generation_id") val remakeGenerationId: Int?
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
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "mascot_pokemon_id") val mascotPokemonId: Int,
    val color: Int
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
