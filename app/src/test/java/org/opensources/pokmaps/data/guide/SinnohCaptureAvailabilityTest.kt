package org.opensources.pokmaps.data.guide

import java.sql.Connection
import java.sql.DriverManager
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.guide.Gen4CaptureGoals

/** Confronte le catalogue du domaine aux rencontres et aux familles de la vraie base distribuée. */
class SinnohCaptureAvailabilityTest {
    @Test
    fun goalsCoverExactlyReachableSpeciesAndTheirOwnRegionalDex() {
        DriverManager.getConnection("jdbc:sqlite:${System.getProperty("pokemaps.database")}").use { database ->
            for (version in 12..14) {
                val group = if (version == 14) 9 else 8
                val seeds = query(database, ENCOUNTERS.replace(":version", version.toString())).map { it[0] }.toSet()
                val evolutions =
                    query(
                        database,
                        """
                    SELECT from_pokemon_id, to_pokemon_id FROM evolution
                    WHERE version_group_id = $group AND trigger != 'trade'
                """
                    )
                val parents =
                    query(
                        database,
                        """
                    SELECT id, evolves_from_id FROM pokemon
                    WHERE generation_id <= 4 AND evolves_from_id IS NOT NULL
                """
                    )
                var reachable = seeds - setOf(377, 378, 379, 442, 486) + setOf(387, 390, 393)
                reachable -= when (version) {
                    12 -> setOf(410)
                    13 -> setOf(408)
                    14 -> emptySet()
                    else -> error("Version de test inattendue")
                }
                // Trois stades au plus ; quatre passes couvrent aussi le retour au bébé par reproduction.
                repeat(4) {
                    reachable = reachable + evolutions.filter { it[0] in reachable }.map { it[1] } +
                        parents.filter { it[0] in reachable }.map { it[1] }
                }
                val national = Gen4CaptureGoals.forVersion(version, true)
                assertEquals("Disponibilité de la version $version", reachable, national.species)
                val dex = if (version == 14) 6 else 5
                val regional = query(database, "SELECT pokemon_id FROM pokedex_entry WHERE pokedex_id=$dex")
                    .map { it[0] }.toSet()
                assertEquals(reachable.intersect(regional), Gen4CaptureGoals.forVersion(version, false).species)
                val trades =
                    query(database, "SELECT pokemon_id FROM encounter WHERE version_id=$version AND method_id=36")
                assertTrue(trades.all { it[0] in reachable })
            }
        }
    }

    private fun query(database: Connection, sql: String): List<List<Int>> =
        database.createStatement().use { statement ->
            statement.executeQuery(sql).use { rows ->
                buildList {
                    while (rows.next()) add((1..rows.metaData.columnCount).map { rows.getInt(it) })
                }
            }
        }
}

private const val ENCOUNTERS = """
    SELECT DISTINCT pokemon_id FROM encounter e
    WHERE version_id=:version AND external_event=0 AND method_id NOT IN (36,48)
    AND NOT EXISTS (
        SELECT 1 FROM encounter_condition ec JOIN encounter_condition_value cv ON cv.id=ec.condition_value_id
        WHERE ec.encounter_id=e.id AND cv.identifier LIKE 'slot2-%' AND cv.identifier!='slot2-none'
    )
"""
