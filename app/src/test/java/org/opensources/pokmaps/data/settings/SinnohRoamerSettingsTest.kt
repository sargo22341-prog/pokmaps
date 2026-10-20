package org.opensources.pokmaps.data.settings

import androidx.datastore.preferences.core.preferencesOf
import androidx.datastore.preferences.core.stringSetPreferencesKey
import java.io.IOException
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.CollectionBackup
import org.opensources.pokmaps.domain.guide.GuideProgress
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class SinnohRoamerSettingsTest {
    private val games = listOf(FakeGameDao.DIAMOND, FakeGameDao.PEARL, FakeGameDao.PLATINUM)

    @Test
    fun emptyObservationsRemainEmptyAndRecordingIsIsolatedByCartridge() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(games))
        assertTrue(settings.progress(12).first().roamerObservations.isEmpty())
        settings.observeRoamer(12, 481, "route-201")
        settings.observeRoamer(13, 481, "route-202")
        assertEquals(mapOf(481 to "route-201"), settings.progress(12).first().roamerObservations)
        assertEquals(mapOf(481 to "route-202"), settings.progress(13).first().roamerObservations)
        assertTrue(settings.progress(14).first().roamerObservations.isEmpty())
        settings.observeRoamer(12, 481, null)
        assertTrue(settings.progress(12).first().roamerObservations.isEmpty())
    }

    @Test(expected = IOException::class)
    fun aWriteFailurePropagates() = runTest {
        val store = FakeDataStore()
        store.writeError = IOException("Disque plein")
        GuideSettings(store, FakeGameDao(games)).observeRoamer(14, 144, "route-201")
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidStoredRouteIsRejectedAtTheBoundary() {
        readRoamerObservations(
            preferencesOf(stringSetPreferencesKey("sinnoh_roamers_14") to setOf("144:route-230")),
            14
        )
    }

    @Test
    fun allFivePlatinumObservationsRoundTripAndMergeWithoutErasingOtherGames() {
        val observations = listOf(481, 488, 144, 145, 146).associateWith { "route-204-north" }
        val backup = CollectionBackup(emptySet(), emptyMap(), mapOf(14 to GuideProgress(emptySet(), observations)))
        val decoded = BackupJson.decode(BackupJson.encode(backup), games)
        assertEquals(backup.guides, decoded.guides)
        val current = backup.copy(guides = mapOf(12 to GuideProgress(roamerObservations = mapOf(481 to "route-201"))))
        val merged = merge(current, decoded)
        assertEquals("route-201", merged.guides[12]?.roamerObservations?.get(481))
        assertEquals(observations, merged.guides[14]?.roamerObservations)
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidImportedObservationIsRejected() {
        val backup = CollectionBackup(emptySet(), emptyMap(), mapOf(14 to GuideProgress()))
        val json = org.json.JSONObject(BackupJson.encode(backup))
        json.getJSONArray("games").getJSONObject(0).getJSONObject("sinnohRoamers").put("144", "route-230")
        BackupJson.decode(json.toString(), games)
    }
}
