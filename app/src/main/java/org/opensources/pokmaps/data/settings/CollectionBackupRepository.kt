package org.opensources.pokmaps.data.settings

import android.content.Context
import android.net.Uri
import androidx.core.net.toUri
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.withContext
import org.opensources.pokmaps.data.db.GameDao
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.validateCollectionBackup
import org.opensources.pokmaps.domain.model.Game
import org.opensources.pokmaps.domain.pokemon.UnownForm

class CollectionBackupRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val store: DataStore<Preferences>,
    private val gamesDao: GameDao
) {
    suspend fun export(address: String) = withContext(Dispatchers.IO) {
        val text = BackupJson.encode(snapshot(store.data.first(), gamesDao.games().first()))
        requireNotNull(context.contentResolver.openOutputStream(document(address), "wt")).use {
            it.write(text.toByteArray(Charsets.UTF_8))
        }
    }

    suspend fun import(address: String): Unit = withContext<Unit>(Dispatchers.IO) {
        val bytes = requireNotNull(context.contentResolver.openInputStream(document(address))).use {
            it.readNBytes(MAX_BYTES + 1)
        }
        require(bytes.size <= MAX_BYTES)
        val games = gamesDao.games().first()
        val imported = BackupJson.decode(String(bytes, Charsets.UTF_8), games)
        store.edit { preferences ->
            val merged = merge(snapshot(preferences, games), imported)
            preferences[key("favorite_pokemon")] = merged.favorites.map { it.toString() }.toSet()
            for (game in games) {
                val version = game.versionId
                preferences[key("caught_pokemon_$version")] =
                    merged.caught[version].orEmpty().map { it.toString() }.toSet()
                val progress = merged.guides[version] ?: GuideProgress()
                preferences[key("guide_completed_$version")] = progress.completed
                if (UnownForm.available(game).isNotEmpty()) {
                    preferences[key("caught_unown_$version")] =
                        merged.unown[version].orEmpty().map { it.identifier }.toSet()
                }
            }
        }
    }

    private fun snapshot(preferences: Preferences, games: List<Game>): CollectionBackup {
        val favorites = preferences[key("favorite_pokemon")].orEmpty().map { it.toInt() }.toSet()
        val caught = games.map { it.versionId }.associateWith { version ->
            preferences[key("caught_pokemon_$version")].orEmpty().map { it.toInt() }.toSet()
        }
        val guides = games.map { it.versionId }.associateWith { version ->
            GuideProgress(preferences[key("guide_completed_$version")].orEmpty())
        }
        val unown = games.filter {
            UnownForm.available(it).isNotEmpty()
        }.map { it.versionId }.associateWith { version ->
            preferences[key("caught_unown_$version")].orEmpty().map(UnownForm::from).toSet()
        }
        return CollectionBackup(favorites, caught, guides, unown).also { validateCollectionBackup(it, games) }
    }

    private fun document(address: String): Uri = address.toUri().also { require(it.scheme == "content") }
    private fun key(name: String) = stringSetPreferencesKey(name)

    private companion object {
        const val MAX_BYTES = 1_000_000
    }
}

internal fun merge(current: CollectionBackup, imported: CollectionBackup): CollectionBackup {
    val caught = (current.caught.keys + imported.caught.keys).associateWith {
        current.caught[it].orEmpty() +
            imported.caught[it].orEmpty()
    }
    val guides = (current.guides.keys + imported.guides.keys).associateWith {
        val existing = current.guides[it] ?: GuideProgress()
        val incoming = imported.guides[it] ?: GuideProgress()
        GuideProgress(existing.completed + incoming.completed)
    }
    val unown = (current.unown.keys + imported.unown.keys).associateWith {
        current.unown[it].orEmpty() +
            imported.unown[it].orEmpty()
    }
    return CollectionBackup(current.favorites + imported.favorites, caught, guides, unown)
}
