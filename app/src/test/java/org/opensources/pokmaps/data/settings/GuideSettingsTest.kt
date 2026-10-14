package org.opensources.pokmaps.data.settings

import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.data.db.FakeGameDao

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
    fun generationThreeCompletionIsKept() = runTest {
        val settings = GuideSettings(FakeDataStore(), FakeGameDao(GAMES))
        settings.complete(9, "hoenn-start", true)
        assertEquals(setOf("hoenn-start"), settings.progress(9).first().completed)
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
