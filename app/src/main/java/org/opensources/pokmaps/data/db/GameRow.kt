package org.opensources.pokmaps.data.db

import androidx.room.Embedded
import androidx.room.Relation
import org.opensources.pokmaps.domain.model.Game

data class GameRecord(
    val versionId: Int,
    val versionIdentifier: String,
    val name: String,
    val versionGroupId: Int,
    val versionGroupIdentifier: String,
    val generationId: Int,
    val mascotPokemonId: Int,
    val color: Int,
    val remakeGenerationId: Int?,
    val hasTimeOfDay: Boolean
)

data class GameRow(
    @Embedded val record: GameRecord,
    @Relation(parentColumn = "versionId", entityColumn = "version_id") val forms: List<PokemonFormEntity>
) {
    fun toGame(): Game {
        val profiles = forms.sortedBy { it.sortOrder }.map { it.toForm() }.groupBy { it.pokemonId }
        check(profiles.values.all { values -> values.count { it.isDefault } == 1 }) {
            "Forme par défaut absente ou ambiguë : ${record.versionIdentifier}"
        }
        return Game(
            record.versionId, record.versionIdentifier, record.name, record.versionGroupId,
            record.versionGroupIdentifier, record.generationId, record.mascotPokemonId, record.color,
            record.remakeGenerationId, record.hasTimeOfDay,
            profiles
        )
    }
}
