package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RegionalMapCatalogTest {
    private val johto = MapInfo(3998, "first-region", "Johto", null, 0, 0, 1000, 1000, 3, isWorld = true)
    private val kanto = johto.copy(id = 3999, identifier = "second-region", name = "Kanto")
    private val route26 = MapInfo(3100, "route-26", "Route 26", johto.id, 100, 100, 100, 100, 0)
    private val route28 = route26.copy(id = 3001, identifier = "route-28", name = "Route 28")
    private val town = route26.copy(id = 3200, identifier = "town", name = "Ville", parentId = kanto.id)
    private val gate = MapInfo(3002, "victory-road-gate", "Porte", null, 0, 0, 100, 100, 1, originMapId = route26.id)
    private val road = gate.copy(id = 3003, identifier = "victory-road", name = "Route Victoire")
    private val house = gate.copy(id = 3004, identifier = "house", name = "Maison", originMapId = town.id)
    private val entrance = MapWarp(2, route26.id, 150, 150, gate.id, 40, 80)
    private val kantoEntrance = MapWarp(5, town.id, 120, 120, house.id, 40, 80)
    private val catalog = MapCatalog(
        "gold-silver",
        listOf(johto, kanto, route26, route28, town, gate, road, house).associateBy { it.id },
        listOf(
            MapWarp(1, route28.id, 110, 110, gate.id, 10, 10),
            entrance,
            MapWarp(3, gate.id, 40, 10, road.id, 40, 80),
            MapWarp(4, gate.id, 40, 80, route26.id, 150, 150),
            kantoEntrance
        ).groupBy { it.mapId },
        emptyMap(),
        emptyMap()
    )

    @Test
    fun worldsAreIdentifiedByDataAndEveryInteriorKeepsItsRegion() {
        assertEquals(listOf(johto, kanto), catalog.worlds)
        assertEquals(johto, catalog.worldOf(road.id))
        assertEquals(kanto, catalog.worldOf(house.id))
        assertEquals(kanto, catalog.displayedMapOf(town.id))
        assertEquals(true, catalog.gameMap(johto.id)?.isWorld)
        assertNull(catalog.parentEntrance(johto.id))
    }

    @Test
    fun curatedOriginWinsOverTheEarlierWarpFromRoute28() {
        assertEquals(entrance, catalog.parentEntrance(gate.id))
        assertEquals(entrance, catalog.worldEntrances()[road.id])
        assertEquals(kantoEntrance, catalog.worldEntrances()[house.id])
    }
}
