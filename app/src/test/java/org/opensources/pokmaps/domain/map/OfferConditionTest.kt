package org.opensources.pokmaps.domain.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.model.EncounterTime

class OfferConditionTest {
    private val potion = OfferItem(17, "potion", "Potion", hasSprite = true)

    @Test
    fun masksGiveTimesAndDaysInPretOrder() {
        // Matin (bit 0) et nuit (bit 2) ; dimanche (bit 0) et lundi (bit 1).
        val condition = OfferCondition.fromMasks(timeMask = 5, weekdayMask = 3, story = listOf("Après le badge Zéphyr"))
        assertEquals(setOf(EncounterTime.MORNING, EncounterTime.NIGHT), condition.times)
        assertEquals(setOf(Weekday.SUNDAY, Weekday.MONDAY), condition.weekdays)
        assertEquals(listOf("Après le badge Zéphyr"), condition.story)
    }

    @Test
    fun nullMasksRestrictNothing() {
        val condition = OfferCondition.fromMasks(null, null, emptyList())
        assertTrue(condition.isAlways)
        assertEquals(OfferCondition.ALWAYS, condition)
    }

    @Test
    fun emptyFullOrOutOfRangeMasksAreRefused() {
        // La génération écrit NULL à la place d'un masque complet ; un masque vide rendrait l'offre impossible.
        listOf(0, 7, 8, -1).forEach { mask ->
            assertThrows(IllegalArgumentException::class.java) { OfferCondition.fromMasks(mask, null, emptyList()) }
        }
        listOf(0, 127, 128).forEach { mask ->
            assertThrows(IllegalArgumentException::class.java) { OfferCondition.fromMasks(null, mask, emptyList()) }
        }
        assertThrows(IllegalArgumentException::class.java) { OfferCondition.fromMasks(null, null, listOf(" ")) }
    }

    @Test
    fun sharedConditionIsShownOnceOnlyWhenAllOffersHaveIt() {
        val afterParcel = OfferCondition(story = listOf("Après avoir remis le colis au Prof. Chen"))
        val mart = listOf(NpcOffer.Sale(potion, 300, afterParcel), NpcOffer.Sale(potion, 200, afterParcel))
        assertEquals(afterParcel, mart.sharedCondition())

        val mixed = listOf(NpcOffer.Sale(potion, 300, afterParcel), NpcOffer.Sale(potion, 200))
        assertNull(mixed.sharedCondition())
        assertNull(listOf(NpcOffer.Sale(potion, 300)).sharedCondition())
        assertNull(emptyList<NpcOffer>().sharedCondition())
    }
}
