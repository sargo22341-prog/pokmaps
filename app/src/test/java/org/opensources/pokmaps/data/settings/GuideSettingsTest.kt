package org.opensources.pokmaps.data.settings

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.guide.RoamerObservation

class GuideSettingsTest {
    @Test
    fun completionIsIsolatedByVersionAndCanBeUnmarked() = runTest {
        val settings = GuideSettings(FakeDataStore())
        settings.complete(1, "kanto-start", true)
        assertEquals(setOf("kanto-start"), settings.progress(1).first().completed)
        assertTrue(settings.progress(2).first().completed.isEmpty())
        settings.complete(1, "kanto-start", false)
        assertTrue(settings.progress(1).first().completed.isEmpty())
    }

    @Test
    fun newObservationReplacesOnlyTheSameBeast() = runTest {
        val settings = GuideSettings(FakeDataStore())
        settings.observeRoamer(4, 243, "route-29")
        settings.observeRoamer(4, 244, "route-30")
        settings.observeRoamer(4, 243, "route-42")
        assertEquals(
            setOf(RoamerObservation(243, "route-42"), RoamerObservation(244, "route-30")),
            settings.progress(4).first().roamers.toSet()
        )
        settings.observeRoamer(4, 243, null)
        assertEquals(listOf(RoamerObservation(244, "route-30")), settings.progress(4).first().roamers)
        assertTrue(settings.progress(5).first().roamers.isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun seaRoutesAreNotValidBeastObservations() = runTest {
        GuideSettings(FakeDataStore()).observeRoamer(4, 243, "route-40")
    }
}
