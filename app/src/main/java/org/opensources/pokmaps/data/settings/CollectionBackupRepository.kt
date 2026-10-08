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
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.opensources.pokmaps.domain.guide.RoamerObservation
import org.opensources.pokmaps.domain.pokemon.UnownForm

class CollectionBackupRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val store: DataStore<Preferences>
) {
    suspend fun export(address: String) = withContext(Dispatchers.IO) {
        val text = BackupJson.encode(snapshot(store.data.first()))
        requireNotNull(context.contentResolver.openOutputStream(document(address), "wt")).use {
            it.write(text.toByteArray(Charsets.UTF_8))
        }
    }

    suspend fun import(address: String): Unit = withContext<Unit>(Dispatchers.IO) {
        val bytes = requireNotNull(context.contentResolver.openInputStream(document(address))).use {
            it.readNBytes(MAX_BYTES + 1)
        }
        require(bytes.size <= MAX_BYTES)
        val imported = BackupJson.decode(String(bytes, Charsets.UTF_8))
        store.edit { preferences ->
            val merged = merge(snapshot(preferences), imported)
            preferences[key("favorite_pokemon")] = merged.favorites.map { it.toString() }.toSet()
            for (version in 1..6) {
                preferences[key("caught_pokemon_$version")] =
                    merged.caught[version].orEmpty().map { it.toString() }.toSet()
                val progress = merged.guides[version] ?: GuideProgress()
                preferences[key("guide_completed_$version")] = progress.completed
                preferences[key("guide_roamers_$version")] =
                    progress.roamers.map { "${it.pokemonId}:${it.place}" }.toSet()
                if (version >= 4) {
                    preferences[key("caught_unown_$version")] =
                        merged.unown[version].orEmpty().map { it.identifier }.toSet()
                }
            }
        }
    }

    private fun snapshot(preferences: Preferences): CollectionBackup {
        val favorites = preferences[key("favorite_pokemon")].orEmpty().map { it.toInt() }.toSet()
        val caught = (1..6).associateWith { version ->
            preferences[key("caught_pokemon_$version")].orEmpty().map { it.toInt() }.toSet()
        }
        val guides = (1..6).associateWith { version ->
            val roamers = preferences[key("guide_roamers_$version")].orEmpty().map {
                val pieces = it.split(":", limit = 2)
                require(pieces.size == 2)
                RoamerObservation(pieces[0].toInt(), pieces[1])
            }
            GuideProgress(preferences[key("guide_completed_$version")].orEmpty(), roamers)
        }
        val unown = (4..6).associateWith { version ->
            preferences[key("caught_unown_$version")].orEmpty().map(UnownForm::from).toSet()
        }
        return CollectionBackup(favorites, caught, guides, unown)
    }

    private fun document(address: String): Uri = address.toUri().also { require(it.scheme == "content") }
    private fun key(name: String) = stringSetPreferencesKey(name)

    private companion object {
        const val MAX_BYTES = 1_000_000
    }
}

internal fun merge(current: CollectionBackup, imported: CollectionBackup): CollectionBackup {
    val caught = (1..6).associateWith { current.caught[it].orEmpty() + imported.caught[it].orEmpty() }
    val guides = (1..6).associateWith {
        val existing = current.guides[it] ?: GuideProgress()
        val incoming = imported.guides[it] ?: GuideProgress()
        val observations = (existing.roamers + incoming.roamers).associateBy { it.pokemonId }.values.toList()
        GuideProgress(existing.completed + incoming.completed, observations)
    }
    val unown = (4..6).associateWith { current.unown[it].orEmpty() + imported.unown[it].orEmpty() }
    return CollectionBackup(current.favorites + imported.favorites, caught, guides, unown)
}
