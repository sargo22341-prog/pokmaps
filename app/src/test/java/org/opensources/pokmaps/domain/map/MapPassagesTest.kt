package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MapPassagesTest {
    private val world = MapInfo(7997, "hoenn", "Hoenn", null, 0, 0, 12800, 9120, 7, isWorld = true)
    private val route111 = MapInfo(7020, "route111", "Route 111", world.id, 1600, 800, 640, 2240, 0)
    private val route130 = MapInfo(7039, "route130", "Chenal 130", world.id, 8960, 4480, 1280, 640, 0)
    private val island =
        MapInfo(7800, "route130-mirage-island", "Île Mirage", null, 0, 0, 12800, 9120, 7, false, route130.id)
    private val base =
        MapInfo(7300, "secret-base-tree1", "Base Secrète (arbre 1)", null, 0, 0, 176, 144, 1, false, route111.id)
    private val shop =
        MapInfo(7100, "route111-house", "Route 111 (maison)", null, 0, 0, 160, 144, 1, false, route111.id)

    private val show = MapWarp(1, route130.id, 9640, 4600, island.id, 9640, 4600, WarpKind.MIRAGE)
    private val hide = MapWarp(2, island.id, 9640, 5000, route130.id, 9640, 5000, WarpKind.MIRAGE)
    private val secret = MapWarp(3, route111.id, 1800, 1000, base.id, 40, 56, WarpKind.SECRET_BASE)
    private val door = MapWarp(4, route111.id, 1900, 1100, shop.id, 72, 120)
    private val berry = MapObject(
        10, island.id, MapObjectKind.ITEM, 9600, 4560, null, 1, "liechi-berry", "Baie Lichii", null, null, null,
        null, "Baie Lichii"
    )

    private fun catalog(islandMap: MapInfo = island) = MapCatalog(
        versionGroupIdentifier = "emerald",
        maps = listOf(world, route111, route130, islandMap, base, shop).associateBy { it.id },
        warps = listOf(show, hide, secret, door).groupBy { it.mapId },
        objects = mapOf(island.id to listOf(berry)),
        areas = emptyMap()
    )

    @Test
    fun theIslandAppearsOnItsRouteOnlyWhileItIsSelected() {
        val catalog = catalog()
        assertEquals(OverlayIsland(island.id, world.id, route130.id, show, hide), catalog.overlayIsland)
        assertFalse(catalog.isIslandShown(world.id, route130.id))
        assertEquals(listOf(door, show), catalog.displayedEntrances(world.id, route130.id))
        assertTrue(catalog.displayedObjects(world.id, route130.id).isEmpty())

        assertTrue(catalog.isIslandShown(world.id, island.id))
        // Le retour, posé sous la plage, remplace l'accès à l'île.
        assertEquals(listOf(door, hide), catalog.displayedEntrances(world.id, island.id))
        assertEquals(listOf(berry), catalog.displayedObjects(world.id, island.id))
    }

    @Test(expected = IllegalArgumentException::class)
    fun anIslandOfAnotherSizeThanItsWorldIsRejected() {
        catalog(island.copy(width = 1280, height = 640, levelCount = 3))
    }

    @Test
    fun secretBasesHaveTheirOwnLayerAndListInsteadOfEntrances() {
        val catalog = catalog()
        val expected = SecretBase(secret, route111.id, "Route 111", base.id, "Base Secrète (arbre 1)")
        assertEquals(listOf(expected), catalog.secretBases)
        assertEquals(listOf(expected), catalog.secretBasesOf(world.id))
        assertFalse(secret in catalog.entrancesOf(world.id))
        assertEquals(listOf(door), catalog.accessibleFrom(route111.id))
        // Une carte modèle n'est l'intérieur d'aucune de ses entrées : le retour suit son lieu d'origine.
        assertNull(catalog.parentEntrance(base.id))
    }

    @Test
    fun aGameWithoutMirageOrBasesHasNeither() {
        val catalog = MapCatalog("red-blue", mapOf(world.id to world), emptyMap(), emptyMap(), emptyMap())
        assertNull(catalog.overlayIsland)
        assertTrue(catalog.secretBases.isEmpty())
    }
}
