package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MapCatalogTest {
    private val world = MapInfo(1999, "kanto", "Kanto", null, 0, 0, 5440, 5760, 6)
    private val pewter = MapInfo(1002, "pewter-city", "Argenta", 1999, 1280, 1280, 640, 576, 0)
    private val route3 = MapInfo(1014, "route-3", "Route 3", 1999, 1280, 992, 1120, 288, 0)
    private val moon1 = MapInfo(1059, "mt-moon-1f", "Mont Sélénite (1er niveau)", null, 0, 0, 640, 576, 3)
    private val moon2 = MapInfo(1060, "mt-moon-b1f", "Mont Sélénite (sous-sol 1)", null, 0, 0, 448, 448, 2)
    private val moon3 = MapInfo(1061, "mt-moon-b2f", "Mont Sélénite (sous-sol 2)", null, 0, 0, 640, 576, 3)

    private val entrance = MapWarp(1, route3.id, 2232, 1048, moon1.id, 232, 552)
    private val catalog = MapCatalog(
        versionGroupIdentifier = "red-blue",
        maps = listOf(world, pewter, route3, moon1, moon2, moon3).associateBy { it.id },
        warps = listOf(
            entrance,
            // Porte large : deux cases vers la même carte
            MapWarp(2, route3.id, 2248, 1048, moon1.id, 248, 552),
            MapWarp(3, moon1.id, 232, 552, route3.id, 2232, 1048),
            MapWarp(4, moon1.id, 88, 88, moon2.id, 72, 72),
            MapWarp(5, moon2.id, 72, 72, moon3.id, 40, 40),
            MapWarp(6, moon2.id, 100, 100, null, null, null)
        ).groupBy { it.mapId },
        objects = emptyMap(),
        areas = emptyMap()
    )

    @Test
    fun displayedMapOfRegionIsTheWorld() {
        assertEquals(world, catalog.world)
        assertEquals(world, catalog.displayedMapOf(pewter.id))
        assertEquals(moon2, catalog.displayedMapOf(moon2.id))
        assertNull(catalog.gameMap(pewter.id))
        assertEquals(listOf(pewter.id, route3.id), catalog.gameMap(world.id)?.regions?.map { it.id })
    }

    @Test
    fun widesDoorsAreMerged() {
        assertEquals(listOf(entrance), catalog.entrancesOf(world.id))
        assertEquals(listOf(5), catalog.entrancesOf(moon2.id).map { it.id })
    }

    @Test
    fun interiorMapsAreReachedFromTheirWorldEntrance() {
        val entrances = catalog.worldEntrances()
        assertEquals(entrance, entrances[moon1.id])
        assertEquals(entrance, entrances[moon3.id])
        assertNull(entrances[world.id])
    }

    @Test
    fun floorsAreParsedFromTheMapIdentifier() {
        assertEquals("mt-moon" to FloorLevel.Basement(2), FloorLevel.parse("mt-moon-b2f"))
        assertEquals("silph-co" to FloorLevel.Storey(10), FloorLevel.parse("silph-co-11f"))
        assertEquals("pokemon-tower" to FloorLevel.Storey(0), FloorLevel.parse("pokemon-tower-1f"))
        assertEquals("celadon-mart" to FloorLevel.Roof, FloorLevel.parse("celadon-mart-roof"))
        assertEquals("rocket-hideout" to FloorLevel.Elevator, FloorLevel.parse("rocket-hideout-elevator"))
        assertNull(FloorLevel.parse("celadon-mansion-roof-house"))
        assertNull(FloorLevel.parse("ss-anne-1f-rooms"))
        assertNull(FloorLevel.parse("route-3"))
    }

    @Test
    fun floorsOfABuildingAreSortedFromTopToBottom() {
        assertEquals(listOf(moon1.id, moon2.id, moon3.id), catalog.floorsOf(moon2.id).map { it.mapId })
        assertTrue(catalog.floorsOf(route3.id).isEmpty())
        assertTrue(catalog.floorsOf(world.id).isEmpty())
    }

    @Test
    fun backGoesUpToTheBuildingEntranceWhateverTheFloor() {
        // Tous les étages du Mont Sélénite remontent à son entrée sur la Route 3.
        assertEquals(entrance, catalog.parentEntrance(moon1.id))
        assertEquals(entrance, catalog.parentEntrance(moon3.id))
        assertNull(catalog.parentEntrance(world.id))

        // Bâtiment dans un bâtiment : on remonte d'un seul niveau.
        val gameCorner = MapInfo(1135, "game-corner", "Casino", null, 0, 0, 320, 288, 2)
        val hideout1 = MapInfo(1199, "rocket-hideout-b1f", "Repaire Rocket (1er sous-sol)", null, 0, 0, 480, 448, 2)
        val hideout2 = MapInfo(1200, "rocket-hideout-b2f", "Repaire Rocket (2e sous-sol)", null, 0, 0, 480, 448, 2)
        val door = MapWarp(10, pewter.id, 1400, 1400, gameCorner.id, 200, 260)
        val stairs = MapWarp(11, gameCorner.id, 270, 40, hideout1.id, 360, 32)
        val nested = MapCatalog(
            versionGroupIdentifier = "red-blue",
            maps = listOf(world, pewter, gameCorner, hideout1, hideout2).associateBy { it.id },
            warps = listOf(
                door,
                stairs,
                MapWarp(12, hideout1.id, 360, 32, gameCorner.id, 270, 40),
                MapWarp(13, hideout1.id, 40, 40, hideout2.id, 40, 40)
            ).groupBy { it.mapId },
            objects = emptyMap(),
            areas = emptyMap()
        )
        assertEquals(stairs, nested.parentEntrance(hideout2.id))
        assertEquals(door, nested.parentEntrance(gameCorner.id))
    }
}
