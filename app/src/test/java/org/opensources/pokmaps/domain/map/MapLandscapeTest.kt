package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MapLandscapeTest {
    @Test
    fun underwaterLevelsBelongOnlyToDiveRoutes() {
        for (group in listOf("emerald", "ruby-sapphire")) {
            val catalog = GeneratedGbaCatalog.load(group)
            val surface = requireNotNull(catalog.mapByIdentifier("hoenn"))
            val underwater = requireNotNull(catalog.mapByIdentifier("hoenn-underwater"))
            assertEquals(listOf(surface), catalog.regionWorlds.filter { it.isWorld })
            assertTrue(catalog.regionWorlds.none { it.id == underwater.id })
            assertEquals(surface, catalog.defaultWorld)
            assertEquals(surface, catalog.regionWorldOf(underwater.id))
            assertTrue(catalog.floorsOf(surface.id).isEmpty())
            assertTrue(catalog.floorsOf(underwater.id).isEmpty())
            for (number in listOf(124, 126, 127, 128, 134)) {
                val route = requireNotNull(catalog.mapByIdentifier("route$number"))
                val floors = catalog.floorsOf(route.id)
                assertEquals(route.id, floors.first().mapId)
                assertEquals(2, floors.size)
                assertEquals(floors, catalog.floorsOf(floors.last().mapId))
                assertEquals(
                    listOf(FloorLevel.Landscape.SURFACE, FloorLevel.Landscape.UNDERWATER),
                    floors.map { it.level }
                )
            }
            for (number in listOf(130, 131, 132, 133)) {
                assertTrue(catalog.floorsOf(requireNotNull(catalog.mapByIdentifier("route$number")).id).isEmpty())
            }
            assertEquals(if (group == "emerald") 7 else 4, catalog.regionsOf(underwater.id).size)
            for (number in listOf(105, 125, 129)) {
                val route = requireNotNull(catalog.mapByIdentifier("route$number"))
                assertEquals(if (group == "emerald") 2 else 0, catalog.floorsOf(route.id).size)
            }
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
        assertEquals(setOf("kanto", "sevii"), remake.regionWorlds.filter { it.isWorld }.map { it.identifier }.toSet())
        val empty = MapCatalog("empty", emptyMap(), emptyMap(), emptyMap(), emptyMap())
        assertTrue(empty.regionWorlds.isEmpty())
        assertTrue(empty.floorsOf(1).isEmpty())
        val surface = requireNotNull(GeneratedGbaCatalog.load("emerald").mapByIdentifier("hoenn"))
        val single = MapCatalog("single", mapOf(surface.id to surface), emptyMap(), emptyMap(), emptyMap())
        assertTrue(single.floorsOf(surface.id).isEmpty())
    }
}
