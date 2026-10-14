package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataMigration
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.stringSetPreferencesKey

/** Retire les dernières positions observées des Pokémon errants : leur suivi a été supprimé des guides. */
internal object ObsoleteRoamerObservations : DataMigration<Preferences> {
    private const val PREFIX = "guide_roamers_"

    override suspend fun shouldMigrate(currentData: Preferences): Boolean =
        currentData.asMap().keys.any { it.name.startsWith(PREFIX) }

    override suspend fun migrate(currentData: Preferences): Preferences {
        val result = currentData.toMutablePreferences()
        currentData.asMap().keys.filter { it.name.startsWith(PREFIX) }
            .forEach { result.remove(stringSetPreferencesKey(it.name)) }
        return result.toPreferences()
    }

    override suspend fun cleanUp() = Unit
}
