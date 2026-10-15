package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Entités de la base pré-remplie pokedex.db, calquées sur tools/pokemaps_data/schema.sql
// (mêmes tables, colonnes, types, NOT NULL, clés primaires et index) : Room vérifie la correspondance
// à l'ouverture et PokedexSchemaTest la vérifie en CI. Les identifiants sont ceux de PokéAPI.

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
    @ColumnInfo(name = "note_fr") val noteFr: String?,
    @ColumnInfo(name = "external_event") val externalEvent: Boolean
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
