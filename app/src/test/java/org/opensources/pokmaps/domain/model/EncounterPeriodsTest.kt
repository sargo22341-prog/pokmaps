package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class EncounterPeriodsTest {
    private fun encounter(time: EncounterTime?, chance: Double = 30.0) = Encounter(
        4, "Or", 1, "Route", 16, "Roucool", "walk", "Marche", 1, false,
        2, 4, chance, 1, null, null, time?.let { setOf(it) }.orEmpty()
    )

    @Test
    fun sharedMorningAndNightEncounterDoesNotKeepTheNightSection() {
        val sections = listOf(encounter(EncounterTime.MORNING), encounter(EncounterTime.NIGHT))
            .byTime(TimeFilter.ALL)
        val shown = EncounterPeriods(sections, setOf(EncounterTime.MORNING)).shown
        assertEquals(listOf(TimeFilter.MORNING), shown.map { it.period })
        assertEquals("Roucool", shown.single().groups.single().encounters.single().pokemonName)
    }

    @Test
    fun giftsFollowAllSelectedWildPeriods() {
        val encounters = listOf(
            encounter(EncounterTime.MORNING),
            encounter(EncounterTime.NIGHT),
            encounter(null).copy(method = "gift", methodName = "Cadeau")
        )
        val shown = EncounterPeriods(encounters.byTime(TimeFilter.ALL), EncounterTime.entries.toSet()).shown
        assertEquals(listOf(TimeFilter.MORNING, TimeFilter.NIGHT, TimeFilter.ALL), shown.map { it.period })
        assertEquals("gift", shown.last().groups.single().encounters.single().method)
    }

    @Test
    fun everyLandPeriodAndGiftPrecedesTheSingleWaterZone() {
        val dry = EncounterTime.entries.map {
            encounter(it, 10.0 + it.ordinal).copy(pokemonId = 16 + it.ordinal)
        }
        val water = EncounterTime.entries.map {
            encounter(it, 20.0 + it.ordinal).copy(method = "surf", methodName = "Surf", pokemonId = 129 + it.ordinal)
        }
        val gift = encounter(null).copy(method = "gift", methodName = "Cadeau")
        val periods = EncounterPeriods((dry + water + gift).byTime(TimeFilter.ALL), EncounterTime.entries.toSet())
        assertEquals(4, periods.drySections.size)
        assertEquals(3, periods.waterSections.size)
        assertEquals(periods.drySections + periods.waterSections, periods.shown)
        assertTrue(periods.drySections.flatMap { it.groups }.none { it.aquatic })
        assertTrue(periods.waterSections.flatMap { it.groups }.all { it.aquatic })
        val night = EncounterPeriods((dry + water).byTime(TimeFilter.ALL), setOf(EncounterTime.NIGHT))
        assertEquals(listOf(TimeFilter.NIGHT), night.drySections.map { it.period })
        assertEquals(listOf(TimeFilter.NIGHT), night.waterSections.map { it.period })
    }

    @Test
    fun identicalPeriodsAndUntimedEncountersNeedNoButtons() {
        val same = EncounterTime.entries.map { encounter(it) }.byTime(TimeFilter.ALL)
        assertTrue(EncounterPeriods(same, emptySet()).available.isEmpty())
        assertEquals(1, EncounterPeriods(same, emptySet()).shown.size)
        val always = listOf(encounter(null)).byTime(TimeFilter.ALL)
        assertTrue(EncounterPeriods(always, emptySet()).available.isEmpty())
        assertTrue(EncounterPeriods(emptyList(), emptySet()).shown.isEmpty())
    }

    @Test
    fun morningOnlyOffersMorningAndCanBeTurnedOff() {
        val sections = listOf(encounter(EncounterTime.MORNING)).byTime(TimeFilter.ALL)
        val periods = EncounterPeriods(sections, EncounterTime.entries.toSet())
        assertEquals(listOf(TimeFilter.MORNING), periods.available)
        assertTrue(EncounterPeriods(sections, periods.toggle(TimeFilter.MORNING)).shown.isEmpty())
    }

    @Test
    fun dayAndNightCanBeSelectedTogetherAndAllRestoresMorning() {
        val sections = EncounterTime.entries.map { encounter(it, 10.0 + it.ordinal) }.byTime(TimeFilter.ALL)
        val periods = EncounterPeriods(sections, EncounterTime.entries.toSet())
        assertEquals(listOf(TimeFilter.MORNING, TimeFilter.DAY, TimeFilter.NIGHT), periods.available)
        val chosen = EncounterPeriods(sections, periods.toggle(TimeFilter.MORNING))
        val shown = chosen.shown.flatMap { it.groups }.flatMap { it.encounters }
        assertEquals(setOf(EncounterTime.DAY, EncounterTime.NIGHT), shown.flatMap { it.times }.toSet())
        assertEquals(EncounterTime.entries.toSet(), chosen.toggle(TimeFilter.ALL))
    }
}
