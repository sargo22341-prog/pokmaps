package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.map.OfferCondition

class ExternalEventTest {
    @Test
    fun theTextDoesNotDecideWhetherAnOfferIsAnExternalEvent() {
        assertFalse(OfferCondition(story = listOf("Carte reçue ; événement externe")).isExternalEvent)
        assertTrue(OfferCondition(story = listOf("Carte reçue"), isExternalEvent = true).isExternalEvent)
        assertFalse(OfferCondition(story = listOf("Après la Ligue")).isExternalEvent)
    }

    @Test
    fun theEditorialLabelOnlyPreventsDuplicateLabels() {
        assertTrue(ExternalEvent.mentioned("Événement externe ; Ticket Aurore"))
        assertFalse(ExternalEvent.mentioned(null))
    }

    @Test
    fun anExternalDistributionIsARestrictionWithoutAnEditorialNote() {
        val condition = OfferCondition(isExternalEvent = true)
        assertFalse(condition.isAlways)
        assertTrue(condition.isExternalEvent)
    }
}
