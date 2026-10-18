package org.opensources.pokmaps.data.settings

import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import org.opensources.pokmaps.domain.pokedex.CaptureScope

class CollectionSettingsTest {
    @Test
    fun corruptFavoritesAreRejectedWithoutDiscardingValues() {
        val store = FakeDataStore()
        val key = stringSetPreferencesKey("favorite_pokemon")
        runTest { store.edit { it[key] = setOf("25", "incorrect") } }
        assertThrows(IllegalArgumentException::class.java) {
            runTest { CollectionSettings(store).favorites.first() }
        }
        runTest { assertEquals(setOf("25", "incorrect"), store.data.first()[key]) }
    }

    @Test
    fun corruptCaptureKeysAndValuesAreRejected() {
        for ((name, values) in listOf(
            "caught_pokemon_invalid" to setOf("25"),
            "caught_pokemon_0" to setOf("25"),
            "caught_pokemon_01" to setOf("25"),
            "caught_pokemon_1" to setOf("025"),
            "caught_pokemon_1" to setOf("-1"),
            "caught_pokemon_1" to setOf("invalid")
        )) {
            val store = FakeDataStore()
            runTest { store.edit { it[stringSetPreferencesKey(name)] = values } }
            assertThrows(IllegalArgumentException::class.java) {
                runTest { CollectionSettings(store).caughtByVersion.first() }
            }
        }
    }

    @Test
    fun aWrongCapturePreferenceTypeIsRejected() {
        val store = FakeDataStore()
        runTest { store.edit { it[stringPreferencesKey("caught_pokemon_1")] = "25" } }
        assertThrows(IllegalArgumentException::class.java) {
            runTest { CollectionSettings(store).caughtByVersion.first() }
        }
    }

    @Test
    fun sinnohCapturesSurviveReopeningAndDoNotReplaceExistingCollections() = runTest {
        val store = FakeDataStore()
        val settings = CollectionSettings(store)
        settings.setCaught(setOf(1), 25, true)
        settings.setCaught(setOf(9), 384, true)
        settings.setFavorite(25, true)
        settings.setCaught(setOf(12), 483, true)
        settings.setCaught(setOf(13), 484, true)
        settings.setCaught(setOf(14), 487, true)
        settings.setCaught(setOf(12, 13, 14), 493, true)

        val reopened = CollectionSettings(store)
        assertEquals(
            mapOf(1 to setOf(25), 9 to setOf(384), 12 to setOf(483, 493), 13 to setOf(484, 493), 14 to setOf(487, 493)),
            reopened.caughtByVersion.first()
        )
        reopened.setCaught(setOf(14), 487, false)
        assertEquals(setOf(493), reopened.caughtByVersion.first()[14])
        assertEquals(setOf(25), reopened.caughtByVersion.first()[1])
        assertEquals(setOf(384), reopened.caughtByVersion.first()[9])
        assertEquals(setOf(25), reopened.favorites.first())
    }

    @Test
    fun validCollectionAndCompatibilityFallbackArePreserved() = runTest {
        val store = FakeDataStore()
        val settings = CollectionSettings(store)
        settings.setCaught(setOf(1, 2), 25, true)
        settings.setFavorite(25, true)
        store.edit { it[stringPreferencesKey("capture_scope")] = "future-scope" }
        assertEquals(mapOf(1 to setOf(25), 2 to setOf(25)), settings.caughtByVersion.first())
        assertEquals(setOf(25), settings.favorites.first())
        assertEquals(CaptureScope.DEFAULT, settings.captureScope.first())
    }
}
