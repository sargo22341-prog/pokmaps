package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map

/** Réglages d'affichage, mémorisés avec DataStore. */
@Singleton
class DisplaySettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    /** Sprites animés (Noir et Blanc) dans le Pokédex et la fiche Pokémon ; activés par défaut. */
    val animatedSprites: Flow<Boolean> =
        dataStore.data.map { it[ANIMATED_SPRITES] ?: DEFAULT_ANIMATED_SPRITES }.distinctUntilChanged()

    suspend fun setAnimatedSprites(enabled: Boolean) {
        dataStore.edit { it[ANIMATED_SPRITES] = enabled }
    }

    private companion object {
        val ANIMATED_SPRITES = booleanPreferencesKey("animated_sprites")
        const val DEFAULT_ANIMATED_SPRITES = true
    }
}
