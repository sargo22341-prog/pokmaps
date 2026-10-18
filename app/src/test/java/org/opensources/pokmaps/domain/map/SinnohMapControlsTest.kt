package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SinnohMapControlsTest {
    private val world = map(1, "sinnoh").copy(isWorld = true)
    private val ground = map(2, "mt-coronet-1f")
    private val upstairs = map(3, "mt-coronet-2f")
    private val lower = map(4, "mt-coronet-1f-lower")
    private val deepest = map(5, "mt-coronet-1f-lower-2")
    private val island = map(6, "newmoon-island-exterior").copy(
        externalEventKey = "newmoon-island",
        eventEntranceOrder = 5
    )

    @Test
    fun sinnohKeepsItsRegionEventDestinationStoreysAndSurfaceLevels() {
        for (group in listOf("diamond-pearl", "platinum")) {
            val catalog = catalog(group)
            assertEquals(world, catalog.defaultWorld)
            assertEquals(listOf(world.id, island.id), catalog.regionWorlds.map { it.id })
            assertTrue(checkNotNull(catalog.gameMap(island.id)).isExternalEvent)
            assertEquals(listOf(upstairs.id, ground.id), catalog.floorsOf(lower.id).map { it.mapId })
            assertEquals(listOf(ground.id, lower.id, deepest.id), catalog.levelsOf(ground.id).map { it.mapId })
            assertEquals(catalog.levelsOf(ground.id), catalog.levelsOf(deepest.id))
            assertTrue(catalog.levelsOf(upstairs.id).isEmpty())
        }
    }

    @Test
    fun eventAreasOnTheMainWorldKeepTheirOwnNamesAndIds() {
        val event = island.copy(parentId = world.id, levelCount = 0, name = "Île Nouvellelune")
        val destinations = MapDestinations.menu(listOf(world), listOf(world, event))
        assertEquals(listOf(world.id, event.id), destinations.map { it.id })
        assertEquals(listOf("sinnoh", "Île Nouvellelune"), destinations.map { it.name })
    }

    @Test
    fun honeyLayerRequiresSinnohTreePositionsOnTheDisplayedMap() {
        val catalog = catalog("platinum")
        assertTrue(catalog.hasHoneyTrees(world.id))
        assertFalse(catalog.hasHoneyTrees(ground.id))
        assertFalse(catalog.copy(versionGroupIdentifier = "gold-silver").hasHoneyTrees(world.id))
        assertFalse(catalog.copy(spots = emptyMap()).hasHoneyTrees(world.id))
    }

    private fun catalog(group: String) = MapCatalog(
        group,
        listOf(world, ground, upstairs, lower, deepest, island).associateBy { it.id },
        emptyMap(),
        emptyMap(),
        emptyMap(),
        spots = mapOf(world.id to listOf(MapSpot(world.id, SpotKind.TREE, 32, 32)))
    )

    private fun map(id: Int, identifier: String) = MapInfo(
        id, identifier, identifier, null, 0, 0, 256, 256, 1
    )
}
