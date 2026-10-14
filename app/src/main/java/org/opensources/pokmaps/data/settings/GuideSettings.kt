package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.first
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.validateGuideProgress

class GuideSettings @Inject constructor(private val dataStore: DataStore<Preferences>, private val gamesDao: GameDao) {
    fun progress(versionId: Int): Flow<GuideProgress> =
        combine(dataStore.data, gamesDao.games()) { preferences, games ->
            require(games.any { it.versionId == versionId }) { "Version absente de la base : $versionId" }
            GuideProgress(preferences[completedKey(versionId)].orEmpty()).also { validateGuideProgress(versionId, it) }
        }

    suspend fun complete(versionId: Int, id: String, completed: Boolean) {
        requireVersion(versionId)
        require(id.matches(ARTICLE))
        dataStore.edit {
            val key = completedKey(versionId)
            it[key] = if (completed) it[key].orEmpty() + id else it[key].orEmpty() - id
        }
    }

    private suspend fun requireVersion(versionId: Int) {
        require(gamesDao.games().first().any { it.versionId == versionId }) {
            "Version absente de la base : $versionId"
        }
    }

    private fun completedKey(versionId: Int) = stringSetPreferencesKey("guide_completed_$versionId")

    private companion object {
        val ARTICLE = Regex("[a-z0-9-]{1,100}")
    }
}
