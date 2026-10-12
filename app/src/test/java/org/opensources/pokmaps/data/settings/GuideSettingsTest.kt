package org.opensources.pokmaps.data.settings

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao
import org.opensources.pokmaps.domain.guide.RoamerObservation

class GuideSettingsTest {
    @Test
    fun completionIsIsolatedByVersionAndCanBeUnmarked() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(GAMES))
        settings.complete(1, "kanto-start", true)
        assertEquals(setOf("kanto-start"), settings.progress(1).first().completed)
        assertTrue(settings.progress(2).first().completed.isEmpty())
        settings.complete(1, "kanto-start", false)
        assertTrue(settings.progress(1).first().completed.isEmpty())
    }

    @Test
    fun newObservationReplacesOnlyTheSameBeast() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(GAMES))
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
        GuideSettings(FakeDataStore(), FakeGameDao(GAMES)).observeRoamer(4, 243, "route-40")
    }

    @Test
    fun generationThreeCompletionIsKept() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(GAMES))
        settings.complete(9, "hoenn-start", true)
        assertEquals(setOf("hoenn-start"), settings.progress(9).first().completed)
    }

    @Test
    fun emeraldChoiceReplacesTheOtherRoamerAndRemakeObservationsAreIsolated() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(GAMES + FakeGameDao.FIRERED))
        settings.observeRoamer(9, 380, "route110")
        settings.observeRoamer(9, 381, "route134")
        assertEquals(listOf(RoamerObservation(381, "route134")), settings.progress(9).first().roamers)
        settings.observeRoamer(10, 244, "route10")
        assertEquals(listOf(RoamerObservation(244, "route10")), settings.progress(10).first().roamers)
        settings.observeRoamer(9, 380, null)
        assertEquals(listOf(RoamerObservation(381, "route134")), settings.progress(9).first().roamers)
        settings.observeRoamer(9, 381, null)
        assertTrue(settings.progress(9).first().roamers.isEmpty())
    }

    @Test(expected = IllegalArgumentException::class)
    fun versionAbsentFromDatabaseIsRejected() = runTest {
        GuideSettings(FakeDataStore(), FakeGameDao()).complete(9, "hoenn-start", true)
    }

    private companion object {
        val GAMES = listOf(
            FakeGameDao.RED,
            FakeGameDao.BLUE,
            FakeGameDao.GOLD,
            FakeGameDao.GOLD.copy(versionId = 5, versionIdentifier = "silver"),
            FakeGameDao.EMERALD
        )
    }
}
