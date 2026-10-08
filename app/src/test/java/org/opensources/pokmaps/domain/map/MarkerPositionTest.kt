package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Test

class MarkerPositionTest {
    private val tower = MapInfo(3001, "radio-tower-5f", "Tour Radio (4e étage)", null, 0, 0, 320, 256, 1)
    private val house = MapInfo(3002, "house", "Maison", null, 0, 0, 128, 128, 1)

    private fun obj(id: Int, mapId: Int, x: Int, y: Int, kind: MapObjectKind = MapObjectKind.NPC) =
        MapObject(id, mapId, kind, x, y, "rocker", null, null, null, null, null, null, null, "Rockeur")

    private fun catalog(vararg objects: MapObject) = MapCatalog(
        versionGroupIdentifier = "gold-silver",
        maps = listOf(tower, house).associateBy { it.id },
        warps = emptyMap(),
        objects = objects.groupBy { it.mapId },
        areas = emptyMap()
    )

    @Test
    fun objectsSharingACellAreSpreadSideBySideWithinIt() {
        // Le cadre Rocket pendant l'occupation et Ben après : même case, deux étapes du scénario.
        val executive = obj(1, tower.id, 216, 88, MapObjectKind.TRAINER)
        val ben = obj(2, tower.id, 216, 88)
        val catalog = catalog(ben, executive)
        assertEquals(MarkerPosition(211, 88), catalog.markerPosition(executive))
        assertEquals(MarkerPosition(221, 88), catalog.markerPosition(ben))
    }

    @Test
    fun threeObjectsKeepTheMiddleOneCentered() {
        val objects = (1..3).map { obj(it, tower.id, 40, 40) }
        val positions = objects.map { catalog(*objects.toTypedArray()).markerPosition(it).x }
        assertEquals(listOf(35, 40, 45), positions)
    }

    @Test
    fun aLoneObjectOrTheSameCellOfAnotherMapStaysCentered() {
        val inTower = obj(1, tower.id, 40, 40)
        val inHouse = obj(2, house.id, 40, 40)
        val catalog = catalog(inTower, inHouse)
        assertEquals(MarkerPosition(40, 40), catalog.markerPosition(inTower))
        assertEquals(MarkerPosition(40, 40), catalog.markerPosition(inHouse))
    }
}
