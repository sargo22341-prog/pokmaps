package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.map.RivalChoice

/** Partie indiquée par l'utilisateur pour les équipes du rival, par groupe de versions, mémorisée avec DataStore. */
@Singleton
class RivalSettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    fun choice(versionGroup: String): Flow<RivalChoice> = dataStore.data.map { preferences ->
        val defaults = RivalChoice()
        RivalChoice(
            starterId = preferences[starterKey(versionGroup)],
            wonLabBattle = preferences[labKey(versionGroup)] ?: defaults.wonLabBattle,
            wonRoute22Battle = preferences[route22Key(versionGroup)] ?: defaults.wonRoute22Battle
        )
    }.distinctUntilChanged()

    suspend fun set(versionGroup: String, choice: RivalChoice) {
        dataStore.edit { preferences ->
            val starter = choice.starterId
            if (starter == null) {
                preferences.remove(starterKey(versionGroup))
            } else {
                preferences[starterKey(versionGroup)] = starter
            }
            preferences[labKey(versionGroup)] = choice.wonLabBattle
            preferences[route22Key(versionGroup)] = choice.wonRoute22Battle
        }
    }

    private fun starterKey(versionGroup: String) = intPreferencesKey("rival_starter_$versionGroup")

    private fun labKey(versionGroup: String) = booleanPreferencesKey("rival_won_lab_$versionGroup")

    private fun route22Key(versionGroup: String) = booleanPreferencesKey("rival_won_route22_$versionGroup")
}
