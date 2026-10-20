package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Test

class Route22RivalTest {
    private val route = MapInfo(1, "route-22", "Route 22", null, 0, 0, 100, 100, 1)
    private val first = MapObject(
        10, 1, MapObjectKind.TRAINER, 20, 30, "blue", null, null, null, null, null, null,
        "rival1", "Rival (1er combat)"
    )
    private val second = first.copy(id = 11, x = 40, name = "Rival (2e combat)")

    @Test
    fun firstGenerationKeepsOneSpriteAndBothBattlesInOrder() {
        val merged = mergeRoute22Rival(listOf(second, first), mapOf(1 to route), 1)
        assertEquals(listOf(first.copy(name = "Rival", battleObjectIds = listOf(10, 11))), merged)
    }

    @Test
    fun otherRoutesAndGenerationsKeepTheirActors() {
        val actors = listOf(first, second)
        assertEquals(actors, mergeRoute22Rival(actors, mapOf(1 to route), 3))
        assertEquals(actors, mergeRoute22Rival(actors, mapOf(1 to route.copy(identifier = "route-23")), 1))
        assertEquals(listOf(first), mergeRoute22Rival(listOf(first), mapOf(1 to route), 1))
    }
}
