package org.opensources.pokmaps.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.model.GameMap
import org.opensources.pokmaps.domain.model.MapRegion

class GameMapTest {
    private val map = GameMap(1999, "kanto", "Kanto", "red-blue", 5440, 5760, 6)

    @Test
    fun tilePathFollowsAssetLayout() {
        assertEquals("maps/red-blue/kanto/5/3_12.webp", map.tilePath(level = 5, row = 3, column = 12))
    }

    @Test
    fun regionBounds() {
        val pallet = MapRegion(1000, "pallet-town", "Bourg Palette", 800, 3744, 320, 288)
        assertEquals(960, pallet.centerX)
        assertEquals(3888, pallet.centerY)
        assertTrue(pallet.contains(800, 3744))
        assertFalse(pallet.contains(1120, 3744))
    }
}
