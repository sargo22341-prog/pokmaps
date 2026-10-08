package org.opensources.pokmaps.domain.map

import java.io.File
import java.sql.Connection
import java.sql.DriverManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

class GeneratedMapSectionsTest {
    @Test
    fun everyBuildingHasOnlyOneBadgePerLevelAndSafariHousesStaySeparate() {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        assumeTrue("Base absente : lancer tools/build_data.py", database.isFile)
        DriverManager.getConnection("jdbc:sqlite:${database.path}").use { connection ->
            val versions = maps(connection).groupBy { it.first }
            val warps = warps(connection)
            assertEquals(setOf(1, 2, 3, 4), versions.keys)
            versions.forEach { (_, entries) ->
                val maps = entries.map { it.second }.associateBy { it.id }
                val catalog = MapCatalog("test", maps, warps, emptyMap(), emptyMap())
                maps.values.filter { it.isDisplayable && !it.isWorld }.forEach { current ->
                    val sections = catalog.floorsOf(current.id)
                    assertTrue(current.identifier, sections.all { it.name.isNotBlank() })
                    assertEquals(sections.size, sections.map { it.level }.distinct().size)
                    val parsed = FloorLevel.parse(current.identifier)
                    if (sections.isNotEmpty()) {
                        assertTrue(current.identifier, sections.any { it.mapId == current.id })
                        if (!current.identifier.endsWith("pokecenter-1f") &&
                            current.identifier != "pokecenter-2f-plan"
                        ) {
                            assertTrue(
                                current.identifier,
                                sections.all {
                                    FloorLevel.parse(maps.getValue(it.mapId).identifier)?.first == parsed?.first
                                }
                            )
                        }
                    }
                }
                assertPlan(catalog, "safari-zone-plan", 4, 0)
                assertPlan(catalog, "mount-mortar-1f-plan", 2, 3)
                assertPlan(catalog, "ice-path-b2f-plan", 2, 4)
                assertPlan(catalog, "whirl-island-1f-plan", 5, 4)
                assertPlan(catalog, "silver-cave-2f-plan", 2, 3)
                assertPlan(catalog, "ss-anne-1f-plan", 3, 4)
                maps.values.filter { it.identifier.startsWith("safari-zone-") && it.identifier.endsWith("house") }
                    .forEach { assertTrue(it.identifier, it.isDisplayable && catalog.floorsOf(it.id).isEmpty()) }
            }
        }
    }

    private fun assertPlan(catalog: MapCatalog, identifier: String, parts: Int, floors: Int) {
        val plan = catalog.mapByIdentifier(identifier) ?: return
        assertTrue(identifier, plan.isDisplayable)
        assertEquals(identifier, parts, catalog.regionsOf(plan.id).size)
        assertEquals(identifier, floors, catalog.floorsOf(plan.id).size)
    }

    private fun maps(connection: Connection): List<Pair<Int, MapInfo>> = connection.createStatement().use { query ->
        query.executeQuery("SELECT * FROM map").use { rows ->
            buildList {
                while (rows.next()) {
                    val parent = rows.getInt("parent_map_id").let { if (rows.wasNull()) null else it }
                    add(
                        rows.getInt("version_group_id") to MapInfo(
                            rows.getInt("id"), rows.getString("identifier"), rows.getString("name_fr"), parent,
                            rows.getInt("x"), rows.getInt("y"), rows.getInt("width"), rows.getInt("height"),
                            rows.getInt("level_count"), rows.getBoolean("is_world")
                        )
                    )
                }
            }
        }
    }

    private fun warps(connection: Connection): Map<Int, List<MapWarp>> = connection.createStatement().use { query ->
        query.executeQuery("SELECT * FROM map_warp").use { rows ->
            buildList {
                while (rows.next()) {
                    val target = rows.getInt("target_map_id").let { if (rows.wasNull()) null else it }
                    add(MapWarp(rows.getInt("id"), rows.getInt("map_id"), 0, 0, target, null, null))
                }
            }.groupBy { it.mapId }
        }
    }
}
