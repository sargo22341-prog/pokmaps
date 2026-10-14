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

    /**
     * Calques qui existaient quand l'utilisateur a choisi ses filtres, par nom ; null pour un choix enregistré
     * avant cette mémorisation. Un calque ajouté depuis s'affiche donc par défaut.
     */
    val knownLayers: Flow<Set<String>?> = dataStore.data.map { it[KNOWN_LAYERS] }.distinctUntilChanged()

    suspend fun setLayers(layers: Set<String>, known: Set<String>) {
        dataStore.edit {
            it[LAYERS] = layers
            it[KNOWN_LAYERS] = known
        }
    }

    private companion object {
        val LAYERS = stringSetPreferencesKey("map_layers")
        val KNOWN_LAYERS = stringSetPreferencesKey("map_layers_known")
    }
}
