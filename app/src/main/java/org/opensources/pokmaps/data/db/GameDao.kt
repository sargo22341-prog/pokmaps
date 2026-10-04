package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query
import kotlinx.coroutines.flow.Flow
import org.opensources.pokmaps.domain.model.Game

@Dao
interface GameDao {
    @Query(
        """
        SELECT v.id AS versionId, v.identifier AS versionIdentifier, v.name_fr AS name,
            vg.id AS versionGroupId, vg.identifier AS versionGroupIdentifier, vg.generation_id AS generationId
        FROM version v JOIN version_group vg ON vg.id = v.version_group_id
        ORDER BY vg.sort_order, v.id
        """
    )
    fun games(): Flow<List<Game>>
}
