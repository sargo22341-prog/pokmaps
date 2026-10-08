package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.pokemon.UnownForm

@Singleton
class UnownSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    val caught: Flow<Map<Int, Set<UnownForm>>> = dataStore.data.map { preferences ->
        preferences.asMap().filter { it.key.name.startsWith(PREFIX) }.map { (key, value) ->
            val version = requireNotNull(key.name.removePrefix(PREFIX).toIntOrNull())
            require(value is Set<*>) { "Collection de Zarbi invalide : ${key.name}" }
            version to value.map { UnownForm.from(requireNotNull(it as? String)) }.toSet()
        }.toMap()
    }

    suspend fun setCaught(versions: Set<Int>, form: UnownForm, caught: Boolean) {
        dataStore.edit { preferences ->
            versions.forEach { version ->
                val key = stringSetPreferencesKey("$PREFIX$version")
                val recorded = preferences[key].orEmpty()
                preferences[key] = if (caught) recorded + form.identifier else recorded - form.identifier
            }
        }
    }

    private companion object {
        const val PREFIX = "caught_unown_"
    }
}
