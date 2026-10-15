package org.opensources.pokmaps.data.db

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.model.Game

@Dao
interface GameDao {
    fun games(): Flow<List<Game>> = gameRows().map { rows -> rows.map { it.toGame() } }

    @Transaction
    @Query(
        """
        SELECT v.id AS versionId, v.identifier AS versionIdentifier, v.name_fr AS name,
            vg.id AS versionGroupId, vg.identifier AS versionGroupIdentifier, vg.generation_id AS generationId,
            v.mascot_pokemon_id AS mascotPokemonId, v.color, vg.remake_generation_id AS remakeGenerationId,
            EXISTS(SELECT 1 FROM encounter e
                JOIN encounter_condition ec ON ec.encounter_id = e.id
                JOIN encounter_condition_value cv ON cv.id = ec.condition_value_id
                WHERE e.version_id = v.id AND cv.identifier IN ('time-morning', 'time-day', 'time-night'))
                AS hasTimeOfDay
        FROM version v JOIN version_group vg ON vg.id = v.version_group_id
        ORDER BY vg.sort_order, v.id
        """
    )
    fun gameRows(): Flow<List<GameRow>>
}
