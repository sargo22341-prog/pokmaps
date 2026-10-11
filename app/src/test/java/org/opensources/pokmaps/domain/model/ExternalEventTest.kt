package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.map.OfferCondition

class ExternalEventTest {
    @Test
    fun eventMapsIncludeTheirRoomsAndHarbors() {
        listOf("faraway-island", "birth-island", "navel-rock", "southern-island").forEach { identifier ->
            assertTrue(ExternalEvent.map(identifier))
            assertTrue(ExternalEvent.map("$identifier-harbor"))
            assertTrue(ExternalEvent.map("$identifier-top"))
        }
        assertFalse(ExternalEvent.map("one-island"))
        assertFalse(ExternalEvent.map("southern-islander"))
    }

    @Test
    fun externalDistributionsAndCuratedConditionsAreRecognized() {
        assertTrue(ExternalEvent.method("colosseum-bonus-disc-jpn"))
        assertTrue(ExternalEvent.method("colosseum-bonus-disc-us"))
        assertTrue(ExternalEvent.method("pokemon-channel-pal"))
        assertFalse(ExternalEvent.method("gift"))
        assertTrue(ExternalEvent.mentioned("Événement externe ; Ticket Aurore"))
        assertFalse(ExternalEvent.mentioned(null))
        assertTrue(OfferCondition(story = listOf("Carte reçue ; événement externe")).isExternalEvent)
        assertFalse(OfferCondition(story = listOf("Après la Ligue")).isExternalEvent)
    }
}
