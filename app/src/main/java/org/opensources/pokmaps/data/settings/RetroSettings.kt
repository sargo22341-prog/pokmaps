package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.guide.RetroGames
import org.opensources.pokmaps.domain.guide.RetroProgress

class RetroSettings @Inject constructor(private val store: DataStore<Preferences>) {
    val progress: Flow<RetroProgress> = store.data.map { preferences ->
        RetroProgress(
            preferences[USERNAME],
            decode(preferences[EARNED].orEmpty()),
            decode(preferences[HARDCORE].orEmpty()),
            preferences[UPDATED]
        )
    }

    suspend fun reset(username: String?) {
        store.edit {
            if (username == null) it.remove(USERNAME) else it[USERNAME] = username
            it.remove(EARNED)
            it.remove(HARDCORE)
            it.remove(UPDATED)
        }
    }

    suspend fun save(progress: RetroProgress) {
        val username = requireNotNull(progress.username)
        val updated = requireNotNull(progress.synchronizedAt)
        require(updated > 0)
        val earned = encode(progress.earned)
        val hardcore = encode(progress.hardcore)
        store.edit {
            it[USERNAME] = username
            it[EARNED] = earned
            it[HARDCORE] = hardcore
            it[UPDATED] = updated
        }
    }

    private fun decode(values: Set<String>): Map<Int, Set<Int>> {
        require(values.size <= MAX_UNLOCKS)
        return values.map { value ->
            val parts = value.split(":")
            require(parts.size == 2)
            val version = parts[0].toInt().also { require(it in RetroGames.ids) }
            val achievement = parts[1].toInt().also { require(it > 0) }
            version to achievement
        }.groupBy({ it.first }, { it.second }).mapValues { it.value.toSet() }
    }

    private fun encode(values: Map<Int, Set<Int>>): Set<String> {
        val encoded = values.flatMap { (version, achievements) ->
            require(version in RetroGames.ids && achievements.all { it > 0 })
            achievements.map { "$version:$it" }
        }.toSet()
        require(encoded.size <= MAX_UNLOCKS)
        return encoded
    }

    private companion object {
        const val MAX_UNLOCKS = 3000
        val USERNAME = stringPreferencesKey("retro_username")
        val EARNED = stringSetPreferencesKey("retro_earned")
        val HARDCORE = stringSetPreferencesKey("retro_hardcore")
        val UPDATED = longPreferencesKey("retro_updated")
    }
}
