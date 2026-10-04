package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map

/** Réglages de la carte, mémorisés avec DataStore. */
@Singleton
class MapSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    /** Calques (filtres) affichés, par nom ; null tant que l'utilisateur ne les a pas changés. */
    val layers: Flow<Set<String>?> = dataStore.data.map { it[LAYERS] }.distinctUntilChanged()

    suspend fun setLayers(layers: Set<String>) {
        dataStore.edit { it[LAYERS] = layers }
    }

    private companion object {
        val LAYERS = stringSetPreferencesKey("map_layers")
    }
}
