package org.opensources.pokmaps.data.settings

import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringSetPreferencesKey
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.model.SpritePlace

/** Sprites animés endroit par endroit, et reprise des deux anciens interrupteurs. */
class DisplaySettingsTest {
    private val legacyApp = booleanPreferencesKey("animated_sprites")
    private val legacyMap = booleanPreferencesKey("map_animated_sprites")

    @Test
    fun withoutAnySettingThePokedexAndPokemonSheetAreAnimated() = runTest {
        assertEquals(SpritePlace.DEFAULT_ANIMATED, DisplaySettings(FakeDataStore()).animatedPlaces.first())
    }

    @Test
    fun theOldSwitchesAreCarriedOver() = runTest {
        val store = FakeDataStore()
        store.edit {
            it[legacyApp] = false
            it[legacyMap] = true
        }
        val settings = DisplaySettings(store)
        assertEquals(setOf(SpritePlace.MAP, SpritePlace.MAP_LIST), settings.animatedPlaces.first())
        // Le premier changement écrit le nouveau réglage et oublie les anciens.
        settings.setAnimated(setOf(SpritePlace.SEARCH), enabled = true)
        assertEquals(
            setOf(SpritePlace.MAP, SpritePlace.MAP_LIST, SpritePlace.SEARCH),
            settings.animatedPlaces.first()
        )
        val stored = store.data.first()
        assertNull(stored[legacyApp])
        assertNull(stored[legacyMap])
    }

    @Test
    fun anUnknownPlaceFromAnotherVersionIsIgnored() = runTest {
        val store = FakeDataStore()
        store.edit { it[stringSetPreferencesKey("animated_sprite_places")] = setOf("map", "hologram") }
        assertEquals(setOf(SpritePlace.MAP), DisplaySettings(store).animatedPlaces.first())
    }
}
