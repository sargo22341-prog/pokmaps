package org.opensources.pokmaps.data.retro

import java.io.IOException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.guide.RetroGames

class RetroSynchronizationTest {
    @Test
    fun manualSynchronizationReadsEachDistinctSetExactlyOnce() = runTest {
        val requests = mutableListOf<Int>()
        val progress = readAllRetroProgress("player") { gameId ->
            requests += gameId
            RetroUnlocks(setOf(gameId), setOf(gameId))
        }
        assertEquals(RetroGames.ids.values.distinct(), requests)
        assertEquals(15, requests.toSet().size)
        for (version in 1..16) {
            assertEquals(setOf(RetroGames.ids.getValue(version)), progress.earned[version])
            assertEquals(progress.earned[version], progress.hardcore[version])
        }
    }

    @Test
    fun sharedHgssSetPopulatesBothVersionsWithoutReadingTheEmptySoulSilverEntry() = runTest {
        val requests = mutableListOf<Int>()
        val progress = readAllRetroProgress("player") { gameId ->
            requests += gameId
            if (gameId == 7212) {
                RetroUnlocks(setOf(124887, 119420), setOf(119420))
            } else {
                RetroUnlocks(emptySet(), emptySet())
            }
        }
        assertEquals(1, requests.count { it == 7212 })
        assertTrue(39076 !in requests)
        assertEquals(setOf(124887, 119420), progress.earned[15])
        assertEquals(setOf(119420), progress.hardcore[15])
        assertEquals(progress.earned[15], progress.earned[16])
        assertEquals(progress.hardcore[15], progress.hardcore[16])
    }

    @Test(expected = IOException::class)
    fun sharedSetFailurePropagatesBeforeSavingEitherRemake() = runTest {
        readAllRetroProgress("player") { gameId ->
            if (gameId == 7212) throw IOException("Hors ligne")
            RetroUnlocks(emptySet(), emptySet())
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
