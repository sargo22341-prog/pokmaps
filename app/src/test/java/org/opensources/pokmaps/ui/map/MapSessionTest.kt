package org.opensources.pokmaps.ui.map

import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class MapSessionTest {
    @Test
    fun cancellationBeforeTheFadeEndsClosesTheRetiredMap() = runTest {
        val session = MapSession(backgroundScope, noTiles)
        var shutdowns = 0
        val retirement = session.retire(600) { shutdowns++ }
        backgroundScope.cancel()
        retirement.join()
        assertEquals(1, shutdowns)
    }

    @Test
    fun retirementKeepsTheMapAliveUntilTheFadeEnds() = runTest {
        val session = MapSession(backgroundScope, noTiles)
        var shutdowns = 0
        val retirement = session.retire(600) { shutdowns++ }
        delay(599)
        assertEquals(0, shutdowns)
        retirement.join()
        assertEquals(1, shutdowns)
    }
}
