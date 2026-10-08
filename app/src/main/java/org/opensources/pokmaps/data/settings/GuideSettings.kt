package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.RoamerObservation
import org.opensources.pokmaps.domain.guide.Roamers
import org.opensources.pokmaps.domain.guide.validateGuideProgress

class GuideSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    fun progress(versionId: Int): Flow<GuideProgress> = dataStore.data.map { preferences ->
        val observations = preferences[roamersKey(versionId)].orEmpty().map { value ->
            val parts = value.split(":", limit = 2)
            require(parts.size == 2 && parts[0].toIntOrNull() in Roamers.pokemonIds && parts[1] in Roamers.places) {
                "Observation de Pokémon errant invalide : $value"
            }
            RoamerObservation(parts[0].toInt(), parts[1])
        }
        require(observations.map { it.pokemonId }.distinct().size == observations.size)
        GuideProgress(preferences[completedKey(versionId)].orEmpty(), observations).also {
            validateGuideProgress(versionId, it)
        }
    }

    suspend fun complete(versionId: Int, id: String, completed: Boolean) {
        require(versionId in 1..6 && id.matches(ARTICLE))
        dataStore.edit {
            val key = completedKey(versionId)
            it[key] = if (completed) it[key].orEmpty() + id else it[key].orEmpty() - id
        }
    }

    suspend fun observeRoamer(versionId: Int, pokemonId: Int, place: String?) {
        require(versionId in 4..6 && pokemonId in Roamers.pokemonIds)
        require(versionId != 6 || pokemonId != 245)
        require(place == null || place in Roamers.places)
        dataStore.edit {
            val key = roamersKey(versionId)
            val others = it[key].orEmpty().filterNot { value -> value.startsWith("$pokemonId:") }.toSet()
            it[key] = if (place == null) others else others + "$pokemonId:$place"
        }
    }

    private fun completedKey(versionId: Int) = stringSetPreferencesKey("guide_completed_$versionId")
    private fun roamersKey(versionId: Int) = stringSetPreferencesKey("guide_roamers_$versionId")

    private companion object {
        val ARTICLE = Regex("[a-z0-9-]{1,100}")
    }
}
