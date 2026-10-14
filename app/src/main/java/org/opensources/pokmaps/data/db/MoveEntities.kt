package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Entités de la base pré-remplie pokedex.db, calquées sur tools/pokemaps_data/schema.sql
// (mêmes tables, colonnes, types, NOT NULL, clés primaires et index) : Room vérifie la correspondance
// à l'ouverture et PokedexSchemaTest la vérifie en CI. Les identifiants sont ceux de PokéAPI.

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
    @ColumnInfo(name = "damage_class") val damageClass: String,
    @ColumnInfo(name = "effect_fr") val effectFr: String,
    @ColumnInfo(name = "effect_chance") val effectChance: Double?
)

@Entity(
    tableName = "item"
)
data class ItemEntity(
    @PrimaryKey val id: Int,
    val identifier: String,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    val category: String,
    @ColumnInfo(name = "has_sprite") val hasSprite: Boolean,
    @ColumnInfo(name = "description_fr") val descriptionFr: String?
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
    primaryKeys = ["pokemon_id", "version_group_id", "move_id", "method", "level"]
)
data class PokemonMoveEntity(
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    @ColumnInfo(name = "version_group_id") val versionGroupId: Int,
    @ColumnInfo(name = "move_id") val moveId: Int,
    val method: String,
    val level: Int,
    @ColumnInfo(name = "version_id") val versionId: Int?
)
