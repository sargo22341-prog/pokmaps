package org.opensources.pokmaps.domain.model

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GameMapTest {
    private val map = GameMap(1999, "kanto", "Kanto", "red-blue", 5440, 5760, 6)

    @Test
    fun tilePathFollowsAssetLayout() {
        assertEquals("maps/red-blue/kanto/5/3_12.webp", map.tilePath(level = 5, row = 3, column = 12))
    }

    @Test
    fun onlyRubyRedrawsTheLilycoveHideoutEntrance() {
        val hoenn = GameMap(997, "hoenn", "Hoenn", "ruby-sapphire", 12800, 9120, 7, isWorld = true)
        assertEquals(
            "maps/ruby-sapphire/hoenn-ruby/6/5_34.webp",
            hoenn.copy(versionIdentifier = "ruby").versionTilePath(level = 6, row = 5, column = 34)
        )
        assertNull(hoenn.copy(versionIdentifier = "sapphire").versionTilePath(0, 0, 0))
        assertNull(hoenn.versionTilePath(0, 0, 0))
        val emerald = hoenn.copy(versionGroupIdentifier = "emerald", versionIdentifier = "emerald")
        assertNull(emerald.versionTilePath(0, 0, 0))
        assertNull(map.copy(versionIdentifier = "red").versionTilePath(0, 0, 0))
        // Le pipeline écrit ces tuiles : le niveau le plus réduit existe toujours.
        val path = requireNotNull(hoenn.copy(versionIdentifier = "ruby").versionTilePath(0, 0, 0))
        assertTrue(path, File("src/main/assets/$path").isFile)
    }

    @Test
    fun onlySeviiHasARepeatedSea() {
        val sevii = GameMap(995, "sevii", "Îles Sevii", "firered-leafgreen", 7488, 10880, 7, isWorld = true)
        assertEquals("maps/firered-leafgreen/sevii-water/3.webp", sevii.seaTilePath(3))
        assertTrue(File("src/main/assets/${sevii.seaTilePath(6)}").isFile)
        assertNull(map.seaTilePath(0))
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
