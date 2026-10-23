package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class HgssMapCatalogTest {
    @Test
    fun preparatoryCatalogStartsInJohtoAndOffersKantoWithoutHoneyTrees() {
        val johto = MapInfo(
            10993, "johto", "Johto", null, 0, 0, 1000, 1000, 3,
            isWorld = true, startMapId = 10060
        )
        val kanto = johto.copy(id = 10992, identifier = "kanto", name = "Kanto", startMapId = 10047)
        val town = MapInfo(10060, "new-bark", "Bourg Geon", johto.id, 100, 100, 100, 100, 0)
        val pallet = town.copy(id = 10047, identifier = "pallet", name = "Bourg Palette", parentId = kanto.id)
        val catalog = MapCatalog(
            "heartgold-soulsilver",
            listOf(kanto, johto, town, pallet).associateBy { it.id },
            emptyMap(),
            emptyMap(),
            emptyMap()
        )
        assertEquals(johto, catalog.defaultWorld)
        assertEquals(setOf("johto", "kanto"), catalog.regionWorlds.map { it.identifier }.toSet())
        assertEquals("new-bark", catalog.maps[catalog.defaultWorld?.startMapId]?.identifier)
        assertEquals(kanto, catalog.worldOf(pallet.id))
        assertFalse(catalog.hasHoneyTrees(town.id))
    }
}
