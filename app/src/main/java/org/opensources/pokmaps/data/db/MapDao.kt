package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query

@Dao
interface MapDao {
    @Query("SELECT * FROM map WHERE version_group_id = :versionGroupId AND identifier = :identifier")
    suspend fun map(versionGroupId: Int, identifier: String): MapEntity?

    /** Villes et routes d'une carte du monde. */
    @Query("SELECT * FROM map WHERE parent_map_id = :mapId ORDER BY id")
    suspend fun regions(mapId: Int): List<MapEntity>
}
