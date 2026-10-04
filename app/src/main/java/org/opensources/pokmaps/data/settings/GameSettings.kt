package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/** Préférences de l'utilisateur, mémorisées avec DataStore. */
@Singleton
class GameSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    /** Version choisie (identifiant PokéAPI), null tant que l'utilisateur n'a rien choisi. */
    val selectedVersionId: Flow<Int?> = dataStore.data.map { it[SELECTED_VERSION] }

    suspend fun selectVersion(versionId: Int) {
        dataStore.edit { it[SELECTED_VERSION] = versionId }
    }

    private companion object {
        val SELECTED_VERSION = intPreferencesKey("selected_version_id")
    }
}
