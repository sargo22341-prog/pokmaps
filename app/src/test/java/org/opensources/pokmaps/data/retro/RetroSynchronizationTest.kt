package org.opensources.pokmaps.data.retro

import java.io.IOException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.guide.RetroGames

class RetroSynchronizationTest {
    @Test
    fun manualSynchronizationReadsEachOfTheFourteenGamesExactlyOnce() = runTest {
        val requests = mutableListOf<Int>()
        val progress = readAllRetroProgress("player") { gameId ->
            requests += gameId
            RetroUnlocks(setOf(gameId), setOf(gameId))
        }
        assertEquals(RetroGames.ids.values.toList(), requests)
        assertEquals(14, requests.toSet().size)
        for (version in 1..14) {
            assertEquals(setOf(RetroGames.ids.getValue(version)), progress.earned[version])
            assertEquals(progress.earned[version], progress.hardcore[version])
        }
    }

    @Test
    fun emptyRemoteCollectionsRemainAValidSuccessfulSynchronization() = runTest {
        val progress = readAllRetroProgress("player") { RetroUnlocks(emptySet(), emptySet()) }
        assertEquals(RetroGames.ids.keys, progress.earned.keys)
        assertTrue(progress.earned.values.all { it.isEmpty() })
        assertTrue(progress.hardcore.values.all { it.isEmpty() })
    }

    @Test(expected = IOException::class)
    fun aReadFailurePropagatesBeforeAnyPartialProgressCanBeSaved() = runTest {
        readAllRetroProgress("player") { gameId ->
            if (gameId == RetroGames.ids.getValue(9)) throw IOException("Hors ligne")
            RetroUnlocks(emptySet(), emptySet())
        }
    }
}
