package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MapSectionsTest {
    @Test
    fun searchDoesNotRepeatASingleRoomOrTheMainHallOfAPlan() {
        val maps = listOf(
            map(1, "single-1f-plan", "Étage"),
            map(2, "single-room", "Étage").copy(parentId = 1, levelCount = 0),
            map(3, "lab-plan", "Labo"),
            map(4, "lab-hall", "Labo").copy(parentId = 3, levelCount = 0),
            map(5, "lab-fossils", "Fossiles").copy(parentId = 3, levelCount = 0)
        )
        assertEquals(setOf(2, 3, 5), catalog(maps).searchableMaps().map { it.id }.toSet())
    }

    @Test
    fun aSharedPokemonCenterFloorKeepsTheGroundFloorOfTheCenterWeEntered() {
        val maps = listOf(
            map(1, "olivine-pokecenter-1f", "Centre Pokémon d'Oliville"),
            map(2, "violet-pokecenter-1f", "Centre Pokémon de Mauville"),
            map(3, "pokecenter-2f-plan", "Centre Pokémon (1er étage)"),
            map(4, "trade-center", "Échanges").copy(parentId = 3, levelCount = 0)
        )
        val catalog = catalog(maps)
        assertEquals(listOf(3, 1), catalog.floorsOf(1).map { it.mapId })
        assertEquals(listOf(3, 2), catalog.floorsOf(4, centerGroundId = 2).map { it.mapId })
    }

    @Test
    fun dividedFloorsHaveOneBadgePerLevelAndExcludeHouses() {
        val maps = listOf(
            map(1, "mount-mortar-1f-plan", "Mont Creuset (RdC)"),
            map(2, "mount-mortar-1f-inside", "Intérieur").copy(parentId = 1, levelCount = 0),
            map(3, "mount-mortar-2f-plan", "Mont Creuset (1er étage)"),
            map(4, "mount-mortar-b1f", "Mont Creuset (sous-sol)"),
            map(5, "mount-mortar-house", "Maison")
        )
        val catalog = catalog(maps)
        assertEquals(listOf(3, 1, 4), catalog.floorsOf(2).map { it.mapId })
        assertTrue(catalog.floorsOf(5).isEmpty())
        assertEquals(FloorLevel.Storey(0), catalog.floorsOf(1).single { it.mapId == 1 }.level)
    }

    @Test
    fun safariZonesShareOnePlanAndHousesKeepTheirOwnEntrance() {
        val maps = listOf(
            map(1, "safari-zone-plan", "Parc Safari"),
            map(2, "safari-zone-center", "Centre").copy(parentId = 1, levelCount = 0),
            map(3, "safari-zone-east", "Est").copy(parentId = 1, x = 352, levelCount = 0),
            map(4, "safari-zone-secret-house", "Maison secrète")
        )
        val passages = listOf(
            MapWarp(1, 2, 312, 100, 3, 360, 100),
            MapWarp(2, 2, 312, 116, 3, 360, 116),
            MapWarp(3, 3, 360, 100, 2, 312, 100),
            MapWarp(4, 3, 500, 200, 4, 100, 100),
            MapWarp(5, 2, 160, 160, 2, 200, 200)
        )
        val catalog = catalog(maps, passages)
        assertEquals(1, catalog.displayedMapOf(3)?.id)
        assertEquals(setOf(2, 3), catalog.gameMap(1)?.regions?.map { it.id }?.toSet())
        assertTrue(catalog.floorsOf(1).isEmpty())
        assertTrue(catalog.floorsOf(4).isEmpty())
        assertEquals(listOf(MapConnection(1, 312, 100, 360, 100)), catalog.connectionsOf(1))
        assertTrue(catalog.entrancesOf(1).any { it.targetMapId == 4 })
    }

    @Test
    fun compositeZonesAndTheirHousesReturnToTheCorrectWorldEntrance() {
        val maps = listOf(
            map(9, "johto", "Johto").copy(isWorld = true),
            map(8, "route-42", "Route 42").copy(parentId = 9, levelCount = 0),
            map(1, "mount-mortar-1f-plan", "Mont Creuset").copy(originMapId = 8),
            map(2, "mount-mortar-1f-outside", "Extérieur").copy(parentId = 1, levelCount = 0, originMapId = 8),
            map(3, "mount-mortar-2f-plan", "Mont Creuset (1er étage)").copy(originMapId = 8),
            map(4, "house", "Maison").copy(originMapId = 8)
        )
        val entry = MapWarp(1, 8, 100, 100, 2, 100, 100)
        val houseEntry = MapWarp(3, 2, 200, 200, 4, 100, 100)
        val catalog = catalog(maps, listOf(entry, MapWarp(2, 2, 150, 150, 3, 100, 100), houseEntry))
        assertEquals(9, catalog.worldOf(2)?.id)
        assertEquals(entry, catalog.parentEntrance(3))
        assertEquals(houseEntry, catalog.parentEntrance(4))
        assertEquals(entry, catalog.worldEntrances()[2])
        assertEquals(entry, catalog.worldEntrances()[4])
    }

    @Test
    fun onlyTheFixedGyaradosAtTheLakeOfRageIsShiny() {
        assertTrue(FixedPokemon.isShiny("lake-of-rage", 130))
        assertFalse(FixedPokemon.isShiny("lake-of-rage", 129))
        assertFalse(FixedPokemon.isShiny("route-43", 130))
        assertFalse(FixedPokemon.isShiny(null, 130))
    }

    private fun map(id: Int, identifier: String, name: String) = MapInfo(id, identifier, name, null, 0, 0, 320, 320, 2)

    private fun catalog(maps: List<MapInfo>, warps: List<MapWarp> = emptyList()) =
        MapCatalog("test", maps.associateBy { it.id }, warps.groupBy { it.mapId }, emptyMap(), emptyMap())
}
