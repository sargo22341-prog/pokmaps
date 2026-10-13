package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

/** Les index du catalogue donnent exactement les résultats des parcours qu'ils remplacent. */
class MapCatalogIndexTest {
    private val groups = listOf("ruby-sapphire", "emerald", "firered-leafgreen")

    @Test
    fun regionsAndPartsMatchAFullScanOfTheMaps() {
        for (group in groups) {
            val catalog = GeneratedGbaCatalog.load(group)
            for (id in catalog.maps.keys + MISSING) {
                val regions = catalog.maps.values.filter { it.parentId == id }.sortedBy { it.id }
                assertEquals(regions, catalog.regionsOf(id))
                assertEquals(listOf(id) + regions.map { it.id }, catalog.partsOf(id))
            }
        }
    }

    @Test
    fun identifiersResolveToTheFirstMapLikeALinearSearch() {
        for (group in groups) {
            val catalog = GeneratedGbaCatalog.load(group)
            for (identifier in catalog.maps.values.map { it.identifier }.distinct()) {
                val first = catalog.maps.values.first { it.identifier == identifier }
                assertSame(first, catalog.mapByIdentifier(identifier))
            }
            assertNull(catalog.mapByIdentifier("lieu-inconnu"))
        }
    }

    @Test
    fun aDuplicateIdentifierKeepsTheFirstMap() {
        val first = MapInfo(1, "maison", "Maison", null, 0, 0, 16, 16, 1)
        val second = first.copy(id = 2, name = "Autre maison")
        val catalog = MapCatalog("red-blue", mapOf(1 to first, 2 to second), emptyMap(), emptyMap(), emptyMap())

        assertSame(first, catalog.mapByIdentifier("maison"))
    }

    @Test
    fun entrancesOfAnUnknownOrInnerMapAreStillComputed() {
        val catalog = GeneratedGbaCatalog.load("emerald")
        val route = catalog.maps.values.first { map ->
            map.parentId != null && catalog.warps[map.id].orEmpty().any { it.targetMapId != null }
        }

        assertEquals(emptyList<MapWarp>(), catalog.entrancesOf(MISSING))
        val entrances = catalog.entrancesOf(route.id)
        assertTrue(entrances.isNotEmpty() && entrances.all { it.mapId == route.id })
    }

    private companion object {
        const val MISSING = -1
    }
}
