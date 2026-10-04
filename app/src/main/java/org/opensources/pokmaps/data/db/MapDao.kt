package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface MapDao {
    @Query("SELECT * FROM map WHERE version_group_id = :versionGroupId ORDER BY id")
    suspend fun maps(versionGroupId: Int): List<MapEntity>

    @Query(
        """
        SELECT w.* FROM map_warp w JOIN map m ON m.id = w.map_id
        WHERE m.version_group_id = :versionGroupId ORDER BY w.id
        """
    )
    suspend fun warps(versionGroupId: Int): List<MapWarpEntity>

    @Query(
        """
        SELECT o.id, o.map_id AS mapId, o.kind, o.x, o.y, o.sprite, o.item_id AS itemId,
            i.identifier AS itemIdentifier, i.name_fr AS itemName, o.pokemon_id AS pokemonId,
            p.name_fr AS pokemonName, o.level, o.trainer_class AS trainerClass
        FROM map_object o
        JOIN map m ON m.id = o.map_id
        LEFT JOIN item i ON i.id = o.item_id
        LEFT JOIN pokemon p ON p.id = o.pokemon_id
        WHERE m.version_group_id = :versionGroupId
        ORDER BY o.id
        """
    )
    suspend fun objects(versionGroupId: Int): List<MapObjectRow>

    @Query(
        """
        SELECT ma.map_id AS mapId, ma.location_area_id AS areaId, la.name_fr AS name
        FROM map_area ma
        JOIN map m ON m.id = ma.map_id
        JOIN location_area la ON la.id = ma.location_area_id
        WHERE m.version_group_id = :versionGroupId
        ORDER BY ma.map_id, la.id
        """
    )
    suspend fun areas(versionGroupId: Int): List<MapAreaRow>

    /** Rencontres des zones d'un lieu dans une version. */
    @Query(
        "SELECT $ENCOUNTER_COLUMNS FROM $ENCOUNTER_TABLES WHERE e.version_id = :versionId AND e.location_area_id IN (:areaIds)"
    )
    suspend fun encounters(versionId: Int, areaIds: List<Int>): List<EncounterRow>

    /** Zones où l'on rencontre un Pokémon dans une version. */
    @Query("SELECT DISTINCT location_area_id FROM encounter WHERE version_id = :versionId AND pokemon_id = :pokemonId")
    suspend fun pokemonAreas(versionId: Int, pokemonId: Int): List<Int>
}
