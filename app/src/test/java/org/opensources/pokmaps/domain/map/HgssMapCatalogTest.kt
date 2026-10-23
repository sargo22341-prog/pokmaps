package org.opensources.pokmaps.domain.map

import java.io.File
import java.sql.DriverManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HgssMapCatalogTest {
    @Test
    fun distributedMapsHaveAlignedSurfaceLevelsAndBothRegions() {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        val maps = DriverManager.getConnection("jdbc:sqlite:${database.path}").use { connection ->
            connection.createStatement().use { statement ->
                statement.executeQuery("SELECT * FROM map WHERE version_group_id=10").use { rows ->
                    buildMap {
                        while (rows.next()) {
                            val parent = rows.getInt("parent_map_id").takeUnless { rows.wasNull() }
                            val map = MapInfo(
                                rows.getInt("id"), rows.getString("identifier"), rows.getString("name_fr"),
                                parent, rows.getInt("x"), rows.getInt("y"), rows.getInt("width"),
                                rows.getInt("height"), rows.getInt("level_count"), rows.getInt("is_world") == 1
                            )
                            put(map.id, map)
                        }
                    }
                }
            }
        }
        assertTrue(maps.size > 720)
        assertEquals(setOf("johto", "kanto"), maps.values.filter { it.isWorld }.map { it.identifier }.toSet())
        val levels = MapLevels.build(maps)
        assertTrue(levels.isNotEmpty())
        for (group in levels.values.distinct()) {
            assertEquals(
                1,
                group.map {
                    maps.getValue(it.mapId).width to maps.getValue(it.mapId).height
                }.distinct().size
            )
        }
    }

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
