package org.opensources.pokmaps.data.repository

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.EncounterRow
import org.opensources.pokmaps.domain.model.EncounterTime

class EncounterConversionTest {
    @Test
    fun nonTimeConditionsKeepCommasInsideTheirDescription() {
        val contest = "Concours de capture d'insectes (mardi, jeudi et samedi)"
        val row = EncounterRow(
            4, "Or", 1, "Parc Naturel", 123, "Insécateur", "walk", "Marche", 1, false,
            12, 15, 5.0, 1, null, "Le matin, $contest", "time-morning,bug-catching-contest-yes", contest
        )
        val encounter = row.toEncounter()
        assertEquals(setOf(EncounterTime.MORNING), encounter.times)
        assertEquals(contest, encounter.nonTimeConditions)
        assertEquals("Le matin, $contest", encounter.conditions)
    }
}
