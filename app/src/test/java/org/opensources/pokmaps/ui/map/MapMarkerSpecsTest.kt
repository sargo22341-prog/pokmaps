package org.opensources.pokmaps.ui.map

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.domain.map.MapObject
import org.opensources.pokmaps.domain.map.MapObjectKind

class MapMarkerSpecsTest {
    private fun element(id: Int, alwaysVisible: Boolean = false): MarkerSpec {
        val obj = MapObject(
            id = id,
            mapId = 1,
            kind = MapObjectKind.TRAINER,
            x = id * 16,
            y = 0,
            sprite = null,
            itemId = null,
            itemIdentifier = null,
            itemName = null,
            pokemonId = null,
            pokemonName = null,
            level = null,
            trainerClass = null,
            name = "Gamin"
        )
        val content = MarkerContent.Element(obj, "red-blue", alwaysVisible, scale = 1f)
        return MarkerSpec(obj.x, obj.y, lazy = !alwaysVisible, zIndex = 1f, pokemon = false, content = content)
    }

    private fun wild(pokemonId: Int): MarkerSpec =
        MarkerSpec(0, 16, false, 1f, true, MarkerContent.Wild(WildMarker(pokemonId, "Rattata", WildMethod.WALK, 0, 16)))

    @Test
    fun identicalMarkersStayInPlace() {
        val drawn = mapOf("o:1" to element(1), "o:2" to element(2), "p:19:0" to wild(19))

        assertEquals(MarkerUpdates(emptyList(), emptyList()), markerUpdates(drawn, LinkedHashMap(drawn)))
    }

    @Test
    fun onlyChangedNewAndRemovedMarkersAreTouched() {
        val drawn = mapOf("o:1" to element(1), "o:2" to element(2), "o:3" to element(3))
        val wanted = linkedMapOf("o:1" to element(1), "o:2" to element(2, alwaysVisible = true), "o:4" to element(4))

        assertEquals(MarkerUpdates(listOf("o:2", "o:3"), listOf("o:2", "o:4")), markerUpdates(drawn, wanted))
    }

    @Test
    fun wildPokemonAreAddedAgainAfterAnElementToStayOnTop() {
        val drawn = mapOf("o:1" to element(1), "p:19:0" to wild(19), "p:16:1" to wild(16))
        val wanted = linkedMapOf(
            "o:1" to element(1),
            "o:2" to element(2),
            "p:19:0" to wild(19),
            "p:16:1" to wild(16)
        )

        assertEquals(
            MarkerUpdates(listOf("p:19:0", "p:16:1"), listOf("o:2", "p:19:0", "p:16:1")),
            markerUpdates(drawn, wanted)
        )
    }

    @Test
    fun removingElementsKeepsTheWildPokemonInPlace() {
        val drawn = mapOf("o:1" to element(1), "o:2" to element(2), "p:19:0" to wild(19))
        val wanted = linkedMapOf("p:19:0" to wild(19))

        assertEquals(MarkerUpdates(listOf("o:1", "o:2"), emptyList()), markerUpdates(drawn, wanted))
    }
}
