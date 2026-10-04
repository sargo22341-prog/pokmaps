package org.opensources.pokmaps.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.MapWarp

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
}
