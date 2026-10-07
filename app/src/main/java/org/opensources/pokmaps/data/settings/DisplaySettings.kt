package org.opensources.pokmaps.data.settings

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.opensources.pokmaps.domain.model.SpritePlace

/** Réglages d'affichage, mémorisés avec DataStore. */
@Singleton
class DisplaySettings @Inject constructor(private val dataStore: DataStore<Preferences>) {
    /** Endroits où les sprites des Pokémon sont animés. */
    val animatedPlaces: Flow<Set<SpritePlace>> = dataStore.data.map { animatedPlaces(it) }.distinctUntilChanged()

    /** Anime (`enabled`) ou fige les sprites de ces endroits, sans toucher aux autres. */
    suspend fun setAnimated(places: Set<SpritePlace>, enabled: Boolean) {
        dataStore.edit { preferences ->
            val current = animatedPlaces(preferences)
            preferences[ANIMATED_PLACES] = (if (enabled) current + places else current - places)
                .map { it.identifier }
                .toSet()
            // Les anciens réglages sont repris une fois dans le nouveau, qui les remplace.
            preferences.remove(LEGACY_ANIMATED_SPRITES)
            preferences.remove(LEGACY_MAP_ANIMATED_SPRITES)
        }
    }

    /**
     * Endroits animés mémorisés. Un identifiant inconnu (réglage écrit par une autre version de l'application) est
     * ignoré, comme les calques de la carte. Sans réglage par endroit, on reprend les deux anciens interrupteurs :
     * « Sprites animés » (Pokédex et fiche Pokémon) et « Sprites animés sur la carte » (carte et liste du lieu).
     */
    private fun animatedPlaces(preferences: Preferences): Set<SpritePlace> {
        preferences[ANIMATED_PLACES]?.let { identifiers ->
            return identifiers.mapNotNull { SpritePlace.fromIdentifier(it) }.toSet()
        }
        val app = preferences[LEGACY_ANIMATED_SPRITES] ?: true
        val map = preferences[LEGACY_MAP_ANIMATED_SPRITES] ?: false
        return buildSet {
            if (app) addAll(SpritePlace.DEFAULT_ANIMATED)
            if (map) addAll(listOf(SpritePlace.MAP, SpritePlace.MAP_LIST))
        }
    }

    private companion object {
        val ANIMATED_PLACES = stringSetPreferencesKey("animated_sprite_places")
        val LEGACY_ANIMATED_SPRITES = booleanPreferencesKey("animated_sprites")
        val LEGACY_MAP_ANIMATED_SPRITES = booleanPreferencesKey("map_animated_sprites")
    }
}
