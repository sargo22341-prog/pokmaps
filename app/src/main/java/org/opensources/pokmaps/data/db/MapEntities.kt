package org.opensources.pokmaps.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

// Entités de la base pré-remplie pokedex.db, calquées sur tools/pokemaps_data/schema.sql
// (mêmes tables, colonnes, types, NOT NULL, clés primaires et index) : Room vérifie la correspondance
// à l'ouverture et PokedexSchemaTest la vérifie en CI. Les identifiants sont ceux de PokéAPI.

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
    @ColumnInfo(name = "level_count") val levelCount: Int,
    @ColumnInfo(name = "is_world") val isWorld: Boolean = false,
    @ColumnInfo(name = "origin_map_id") val originMapId: Int? = null,
    @ColumnInfo(name = "start_map_id") val startMapId: Int? = null
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
    @ColumnInfo(name = "trainer_class") val trainerClass: String?,
    @ColumnInfo(name = "name_fr") val nameFr: String,
    /** Version où l'objet est ainsi (Ho-Oh et Lugia d'Or et d'Argent), null s'il vaut pour tout le jeu. */
    @ColumnInfo(name = "version_id") val versionId: Int?
)

@Entity(
    tableName = "trainer_pokemon",
    primaryKeys = ["map_object_id", "slot"]
)
data class TrainerPokemonEntity(
    @ColumnInfo(name = "map_object_id") val mapObjectId: Int,
    val slot: Int,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int,
    val level: Int,
    @ColumnInfo(name = "move1_id") val move1Id: Int?,
    @ColumnInfo(name = "move2_id") val move2Id: Int?,
    @ColumnInfo(name = "move3_id") val move3Id: Int?,
    @ColumnInfo(name = "move4_id") val move4Id: Int?
)

@Entity(
    tableName = "npc_offer",
    indices = [
        Index("map_object_id", name = "index_npc_offer_map_object_id")
    ]
)
data class NpcOfferEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "map_object_id") val mapObjectId: Int,
    val kind: String,
    @ColumnInfo(name = "item_id") val itemId: Int?,
    @ColumnInfo(name = "pokemon_id") val pokemonId: Int?,
    val quantity: Int?,
    val price: Int?,
    @ColumnInfo(name = "wanted_pokemon_id") val wantedPokemonId: Int?,
    @ColumnInfo(name = "wanted_item_id") val wantedItemId: Int?,
    @ColumnInfo(name = "version_id") val versionId: Int?,
    @ColumnInfo(name = "time_mask") val timeMask: Int?,
    @ColumnInfo(name = "weekday_mask") val weekdayMask: Int?,
    val currency: String?
)

@Entity(
    tableName = "npc_offer_story",
    primaryKeys = ["npc_offer_id", "slot"]
)
data class NpcOfferStoryEntity(
    @ColumnInfo(name = "npc_offer_id") val npcOfferId: Int,
    val slot: Int,
    @ColumnInfo(name = "description_fr") val descriptionFr: String
)

@Entity(
    tableName = "map_spot",
    indices = [
        Index("map_id", name = "index_map_spot_map_id")
    ]
)
data class MapSpotEntity(
    @PrimaryKey val id: Int,
    @ColumnInfo(name = "map_id") val mapId: Int,
    val kind: String,
    val x: Int,
    val y: Int
)
