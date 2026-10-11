package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MapLandscapeTest {
    @Test
    fun underwaterSharesHoennRegionAndBothWorldLevels() {
        for (group in listOf("emerald", "ruby-sapphire")) {
            val catalog = GeneratedGbaCatalog.load(group)
            val surface = requireNotNull(catalog.mapByIdentifier("hoenn"))
            val underwater = requireNotNull(catalog.mapByIdentifier("hoenn-underwater"))
            assertEquals(listOf(surface), catalog.regionWorlds)
            assertEquals(surface, catalog.defaultWorld)
            assertEquals(surface, catalog.regionWorldOf(underwater.id))
            val floors = catalog.floorsOf(surface.id)
            assertEquals(listOf(surface.id, underwater.id), floors.map { it.mapId })
            assertEquals(floors, catalog.floorsOf(underwater.id))
            assertEquals(listOf(FloorLevel.Landscape.SURFACE, FloorLevel.Landscape.UNDERWATER), floors.map { it.level })
        }
    }

    @Test
    fun tidesAndIceRoomAreReachableFromEveryTideLevel() {
        for (group in listOf("emerald", "ruby-sapphire")) {
            val catalog = GeneratedGbaCatalog.load(group)
            val high = requireNotNull(catalog.mapByIdentifier("shoal-cave-high-tide-1f-plan"))
            val floors = catalog.floorsOf(high.id)
            assertEquals(
                listOf(
                    FloorLevel.Landscape.HIGH_TIDE,
                    FloorLevel.Landscape.LOW_TIDE,
                    FloorLevel.Landscape.LOW_TIDE_BASEMENT
                ),
                floors.map { it.level }
            )
            floors.forEach { assertEquals(floors, catalog.floorsOf(it.mapId)) }
            assertTrue(floors.all { it.name.isNotBlank() })
        }
    }

    @Test
    fun otherRegionsAndMissingLevelsRemainIndependent() {
        val remake = GeneratedGbaCatalog.load("firered-leafgreen")
        assertEquals(setOf("kanto", "sevii"), remake.regionWorlds.map { it.identifier }.toSet())
        val empty = MapCatalog("empty", emptyMap(), emptyMap(), emptyMap(), emptyMap())
        assertTrue(empty.regionWorlds.isEmpty())
        assertTrue(empty.floorsOf(1).isEmpty())
        val surface = requireNotNull(GeneratedGbaCatalog.load("emerald").mapByIdentifier("hoenn"))
        val single = MapCatalog("single", mapOf(surface.id to surface), emptyMap(), emptyMap(), emptyMap())
        assertTrue(single.floorsOf(surface.id).isEmpty())
    }
}
