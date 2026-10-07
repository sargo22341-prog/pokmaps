package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class WorldZoomTest {
    @Test
    fun theWorldCanBeZoomedOutBeyondTheWholeMap() {
        // Vue en portrait : la largeur limite (1 000 / 2 000), puis le recul supplémentaire.
        assertEquals(0.5 * WorldZoom.ZOOM_OUT, checkNotNull(WorldZoom.minScale(1000, 2000, 2000, 1800)), 1e-9)
        // Vue en paysage : c'est la hauteur qui limite (1 000 / 1 800).
        assertEquals(1000.0 / 1800 * WorldZoom.ZOOM_OUT, checkNotNull(WorldZoom.minScale(2000, 1000, 2000, 1800)), 1e-9)
    }

    @Test
    fun noMinimumBeforeTheViewIsLaidOut() {
        assertNull(WorldZoom.minScale(0, 0, 2000, 1800))
        assertNull(WorldZoom.minScale(1000, 0, 2000, 1800))
    }

    @Test(expected = IllegalArgumentException::class)
    fun anEmptyMapIsRejected() {
        WorldZoom.minScale(1000, 2000, 0, 1800)
    }
}
