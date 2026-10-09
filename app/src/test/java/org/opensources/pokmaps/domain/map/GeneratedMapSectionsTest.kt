package org.opensources.pokmaps.domain.map

import java.io.File
import java.sql.Connection
import java.sql.DriverManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GeneratedMapSectionsTest {
    @Test
    fun hoennPlansKeepRoomsTogetherAndVariantsSeparate() {
        for (group in listOf("emerald", "ruby-sapphire")) {
            val catalog = GeneratedGbaCatalog.load(group)
            assertEquals(setOf("hoenn", "hoenn-underwater"), catalog.worlds.map { it.identifier }.toSet())
            listOf(
                "granite-cave-1f-plan",
                "seafloor-cavern-1f-plan",
                "shoal-cave-high-tide-1f-plan",
                "shoal-cave-low-tide-1f-plan",
                "sky-pillar-1f-plan"
            ).forEach { assertTrue(it, catalog.mapByIdentifier(it) != null) }
            assertPlan(catalog, "granite-cave-1f-plan", 2, 3)
            assertPlan(catalog, "seafloor-cavern-1f-plan", 10, 0)
            assertPlan(catalog, "shoal-cave-high-tide-1f-plan", 2, 0)
            assertPlan(catalog, "shoal-cave-low-tide-1f-plan", 4, 2)
            assertPlan(catalog, "sky-pillar-1f-plan", 1, 6)
            val origin = catalog.mapByIdentifier("cave-of-origin-1f-plan")
            requireNotNull(origin)
            assertEquals(if (group == "emerald") 2 else 5, catalog.floorsOf(origin.id).size)
            catalog.maps.values.filter { it.isDisplayable && !it.isWorld }.forEach { map ->
                val floors = catalog.floorsOf(map.id)
                assertEquals(map.identifier, floors.size, floors.map { it.level }.distinct().size)
            }
            assertTrue(catalog.mapByIdentifier("route130-mirage-island")?.isDisplayable == true)
        }
    }

    @Test
    fun remakePlansKeepKantoSeviiAndBranchFloorsSeparate() {
        val catalog = GeneratedGbaCatalog.load("firered-leafgreen")
        assertEquals(setOf("kanto", "sevii"), catalog.worlds.map { it.identifier }.toSet())
        val requiredPlans = listOf(
            "silph-co-1f-plan", "pokemon-tower-1f-plan", "cerulean-cave-1f-plan", "victory-road-1f-plan",
            "seafoam-islands-1f-plan", "mt-ember-ruby-path-b1f-plan", "mt-ember-summit-path-1f-plan",
            "tanoby-ruins-plan", "navel-rock-1f-plan", "navel-rock-summit-path-2f-plan",
            "navel-rock-base-path-b1f-plan"
        )
        requiredPlans.forEach { assertTrue(it, catalog.mapByIdentifier(it) != null) }
        assertPlan(catalog, "silph-co-1f-plan", 1, 12)
        assertPlan(catalog, "pokemon-tower-1f-plan", 1, 7)
        assertPlan(catalog, "cerulean-cave-1f-plan", 1, 3)
        assertPlan(catalog, "victory-road-1f-plan", 1, 3)
        assertPlan(catalog, "seafoam-islands-1f-plan", 1, 5)
        assertPlan(catalog, "mt-ember-ruby-path-b1f-plan", 2, 6)
        assertPlan(catalog, "mt-ember-summit-path-1f-plan", 1, 4)
        assertPlan(catalog, "tanoby-ruins-plan", 7, 0)
        assertPlan(catalog, "navel-rock-1f-plan", 1, 3)
        assertPlan(catalog, "navel-rock-summit-path-2f-plan", 1, 5)
        assertPlan(catalog, "navel-rock-base-path-b1f-plan", 1, 12)
        val island = requireNotNull(catalog.mapByIdentifier("four-island"))
        assertEquals("sevii", catalog.worldOf(island.id)?.identifier)
        val town = requireNotNull(catalog.mapByIdentifier("pallet-town"))
        assertEquals("kanto", catalog.worldOf(town.id)?.identifier)
        assertTrue(catalog.maps.values.none { "prototype" in it.identifier || "unused" in it.identifier })
        catalog.maps.values.filter { it.isDisplayable && !it.isWorld }.forEach { map ->
            val floors = catalog.floorsOf(map.id)
            assertEquals(map.identifier, floors.size, floors.map { it.level }.distinct().size)
        }
    }

    @Test
    fun everyBuildingHasOnlyOneBadgePerLevelAndSafariHousesStaySeparate() {
        val database = File(System.getProperty("pokemaps.database").orEmpty())
        assertTrue("Asset versionné absent : database/pokedex.db", database.isFile)
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
