package org.opensources.pokmaps.data.repository

import org.junit.Assert.assertEquals
import org.junit.Test
import org.opensources.pokmaps.data.db.EncounterRow
import org.opensources.pokmaps.domain.model.EncounterTime

class EncounterConversionTest {
    @Test
    fun conditionIdentifiersAndLabelsReachTheRouteFilterWithoutSplittingFrenchCommas() {
        val text = "Après un badge, puis un dialogue"
        val row = EncounterRow(
            12, "Diamant", 1, "Route", 16, "Roucool", "walk", "Marche", 1, false,
            2, 4, 20.0, 1, null, text, conditionIdentifiers = "slot2-ruby,other-story",
            conditionLabels = "slot2-ruby\u001fRubis\u001eother-story\u001f$text"
        )
        val encounter = row.toEncounter()
        assertEquals(setOf("slot2-ruby", "other-story"), encounter.conditionKeys)
        assertEquals(mapOf("slot2-ruby" to "Rubis", "other-story" to text), encounter.conditionNames)
    }

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
