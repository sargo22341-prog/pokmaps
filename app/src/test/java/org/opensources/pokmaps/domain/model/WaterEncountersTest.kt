package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WaterEncountersTest {
    @Test
    fun specialFishingTilesAndDivingStayInTheWaterZone() {
        val fishing = encounter("feebas-tile-fishing").copy(chance = null)
        val water = listOf(fishing, encounter("seaweed"))
        val periods = EncounterPeriods(water.byTime(TimeFilter.ALL), EncounterTime.entries.toSet())
        assertTrue(periods.drySections.isEmpty())
        assertTrue(periods.waterSections.isNotEmpty())
        val species = listOf(fishing).groupByMethod().single().species.single()
        assertTrue(species.waterMethods.getValue(WaterMethod.SURF).isEmpty())
        for (method in listOf(WaterMethod.OLD_ROD, WaterMethod.GOOD_ROD, WaterMethod.SUPER_ROD)) {
            assertEquals(listOf(fishing), species.waterMethods.getValue(method))
        }
    }

    private fun encounter(method: String, chance: Double = 30.0, version: Int = 1) = Encounter(
        version, "Version", 1, "Route", 129, "Magicarpe", method, method, 1, false,
        5, 10, chance, 1, null, null
    )

    @Test
    fun waterMethodsShareOneSpeciesAcrossAllGames() {
        for (version in 1..14) {
            val encounters = WaterMethod.entries.map { encounter(it.identifier, version = version) }
            val group = encounters.groupByMethod().single()
            assertTrue(group.aquatic)
            val species = group.species.single()
            assertEquals(WaterMethod.entries, species.waterMethods.keys.toList())
            assertTrue(species.waterMethods.values.all { it.size == 1 })
            assertEquals(encounters.toSet(), species.encounters.toSet())
        }
    }

    @Test
    fun unavailableMethodsStayEmptyAndProbabilitiesRemainIndependent() {
        val encounters = listOf(encounter("surf", 10.0), encounter("old-rod", 70.0))
        val species = encounters.byTime(TimeFilter.ALL).single().methods.single().species.single()
        assertEquals(10.0, species.waterMethods.getValue(WaterMethod.SURF).single().chance)
        assertEquals(70.0, species.waterMethods.getValue(WaterMethod.OLD_ROD).single().chance)
        assertTrue(species.waterMethods.getValue(WaterMethod.GOOD_ROD).isEmpty())
        assertTrue(species.waterMethods.getValue(WaterMethod.SUPER_ROD).isEmpty())
    }

    @Test
    fun locationsVersionsAndNonWaterMethodsRemainSeparate() {
        val surf = encounter("surf")
        val encounters = listOf(surf, surf.copy(areaId = 2), surf.copy(versionId = 2), encounter("walk"))
        val groups = encounters.groupByMethod()
        assertEquals(3, groups.first { it.aquatic }.species.size)
        assertFalse(groups.first { !it.aquatic }.aquatic)
    }

    @Test
    fun conditionalAndHourlyVariantsKeepTheirOwnLevelsAndChances() {
        val surf = encounter("surf").copy(times = setOf(EncounterTime.NIGHT))
        val swarm = surf.copy(chance = 50.0, minLevel = 20, conditions = "Essaim", nonTimeConditions = "Essaim")
        val sections = listOf(surf, swarm, encounter("old-rod")).byTime(TimeFilter.ALL)
        val night = sections.first { it.period == TimeFilter.NIGHT }.methods.single()
        assertTrue(night.aquatic)
        assertEquals(setOf(surf, swarm), night.species.single().waterMethods.getValue(WaterMethod.SURF).toSet())
    }
}
