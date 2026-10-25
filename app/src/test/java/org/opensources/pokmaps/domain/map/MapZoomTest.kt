package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.model.GameMap

class MapZoomTest {
    @Test
    fun hgssWorldKeepsItsLimitInPortraitAndLandscapeWithoutLimitingCaves() {
        val world = GameMap(10993, "johto", "Johto et Kanto", "heartgold-soulsilver", 22658, 8192, 8, isWorld = true)
        assertEquals(0.5, checkNotNull(MapZoom.worldMinimumScale(world)), 1e-9)
        assertEquals(0.5, checkNotNull(MapZoom.minScale(1440, 2387, world)), 1e-9)
        assertEquals(0.5, checkNotNull(MapZoom.minScale(2387, 1440, world)), 1e-9)
        assertNull(MapZoom.minScale(0, 0, world))
        val cave = world.copy(isWorld = false)
        assertNull(MapZoom.worldMinimumScale(cave))
        assertEquals(1440.0 / 22658 * MapZoom.ZOOM_OUT, checkNotNull(MapZoom.minScale(1440, 2387, cave)), 1e-9)
    }

    @Test
    fun aWidePlanFitsCompletelyOnAPortraitPhone() {
        val scale = checkNotNull(MapZoom.minScale(1440, 2200, 1568, 1024))
        assertTrue(1568 * scale < 1440)
        assertTrue(1024 * scale < 2200)
    }

    @Test
    fun theWorldCanBeZoomedOutBeyondTheWholeMap() {
        // Vue en portrait : la largeur limite (1 000 / 2 000), puis le recul supplémentaire.
        assertEquals(0.5 * MapZoom.ZOOM_OUT, checkNotNull(MapZoom.minScale(1000, 2000, 2000, 1800)), 1e-9)
        // Vue en paysage : c'est la hauteur qui limite (1 000 / 1 800).
        assertEquals(1000.0 / 1800 * MapZoom.ZOOM_OUT, checkNotNull(MapZoom.minScale(2000, 1000, 2000, 1800)), 1e-9)
    }

    @Test
    fun noMinimumBeforeTheViewIsLaidOut() {
        assertNull(MapZoom.minScale(0, 0, 2000, 1800))
        assertNull(MapZoom.minScale(1000, 0, 2000, 1800))
    }

    @Test(expected = IllegalArgumentException::class)
    fun anEmptyMapIsRejected() {
        MapZoom.minScale(1000, 2000, 0, 1800)
    }
}
