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
        val maps = distributedMaps()
        assertEquals(711, maps.size)
        assertEquals(setOf("johto", "kanto"), maps.values.filter { it.isWorld }.map { it.identifier }.toSet())
        val levels = MapLevels.build(maps)
        assertTrue(levels.isNotEmpty())
        assertTrue(maps.values.filter { it.isWorld }.all { levels[it.id].isNullOrEmpty() })
        val houses = maps.values.filter {
            it.identifier.startsWith("cherrygrove-") &&
                (it.identifier.endsWith("-house") || it.identifier == "cherrygrove-pokemart")
        }
        assertEquals(4, houses.size)
        assertTrue(houses.all { it.isDisplayable })
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
    fun safariAtlasContainsTwelveHabitatsAndTheEntranceWithoutSideSelectors() {
        val maps = distributedMaps()
        val catalog = MapCatalog("heartgold-soulsilver", maps, emptyMap(), emptyMap(), emptyMap())
        val atlas = requireNotNull(catalog.mapByIdentifier("safari-atlas"))
        val entrance = requireNotNull(catalog.mapByIdentifier("safari-zone-entrance-exterior"))
        val regions = catalog.regionsOf(atlas.id)
        assertEquals(13, regions.size)
        assertEquals(atlas, catalog.displayedMapOf(entrance.id))
        assertTrue(catalog.floorsOf(atlas.id).isEmpty())
        assertTrue(catalog.levelsOf(atlas.id).isEmpty())
        val order = listOf(1, 2, 3, 7, 8, 9, 4, 5, 6, 10, 11, 12)
        val habitats = order.map { number ->
            requireNotNull(catalog.mapByIdentifier("safari-zone-${number.toString().padStart(2, '0')}"))
        }
        assertEquals(1, habitats.take(6).map { it.y }.distinct().size)
        assertEquals(1, habitats.drop(6).map { it.y }.distinct().size)
        assertTrue(habitats.all { it.y < entrance.y })
        assertEquals(habitats[1].x, entrance.x)
        habitats.forEach { habitat ->
            assertEquals(atlas, catalog.displayedMapOf(habitat.id))
            assertTrue(catalog.floorsOf(habitat.id).isEmpty())
            assertTrue(habitat.x >= 0 && habitat.x + habitat.width <= atlas.width)
            assertTrue(habitat.y >= 0 && habitat.y + habitat.height <= atlas.height)
        }
    }

    private fun distributedMaps(): Map<Int, MapInfo> {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        return DriverManager.getConnection("jdbc:sqlite:${database.path}").use { connection ->
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
