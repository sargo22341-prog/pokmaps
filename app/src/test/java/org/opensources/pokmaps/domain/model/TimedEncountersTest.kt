package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TimedEncountersTest {
    private fun encounter(time: EncounterTime?, chance: Double = 30.0, condition: String? = null) = Encounter(
        4, "Or", 1, "Route", 16, "Roucool", "walk", "Marche", 1, false,
        2, 4, chance, 1, null, time?.name, time?.let { setOf(it) }.orEmpty(), condition
    )

    @Test
    fun identicalTablesBecomeOneAlwaysEncounter() {
        val sections = EncounterTime.entries.map { encounter(it) }.byTime(TimeFilter.ALL)
        assertEquals(TimeFilter.ALL, sections.single().period)
        val merged = sections.single().groups.single().encounters.single()
        assertEquals(30.0, merged.chance)
        assertEquals(EncounterTime.entries.toSet(), merged.times)
        assertEquals(null, merged.conditions)
    }

    @Test
    fun probabilitiesAndOtherConditionsRemainSeparate() {
        val encounters = listOf(
            encounter(EncounterTime.MORNING),
            encounter(EncounterTime.DAY),
            encounter(EncounterTime.NIGHT, 10.0),
            encounter(EncounterTime.NIGHT, condition = "Essaim")
        )
        val sections = encounters.byTime(TimeFilter.ALL)
        assertEquals(listOf(TimeFilter.ALL, TimeFilter.NIGHT), sections.map { it.period })
        assertEquals(2, sections.first().methods.single().species.single().encounters.size)
        assertEquals(1, sections.last().groups.single().encounters.size)
    }

    @Test
    fun untimedEncountersAreIncludedInEachSpecificFilter() {
        val encounters = listOf(encounter(null), encounter(EncounterTime.NIGHT, 10.0))
        assertEquals(1, encounters.byTime(TimeFilter.DAY).single().groups.single().encounters.size)
        assertEquals(2, encounters.byTime(TimeFilter.NIGHT).single().groups.single().encounters.size)
        assertTrue(emptyList<Encounter>().byTime(TimeFilter.ALL).isEmpty())
    }

    @Test
    fun cycleHasOnePeriodAndReturnsToAll() {
        var filter = TimeFilter.ALL
        repeat(3) {
            filter = filter.next()
            assertEquals(1, filter.times.size)
        }
        assertEquals(TimeFilter.ALL, filter.next())
    }
}
