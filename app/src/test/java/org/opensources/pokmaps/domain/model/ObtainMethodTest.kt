package org.opensources.pokmaps.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ObtainMethodTest {
    @Test
    fun everyMethodOfTheGeneratedDatabaseIsClassified() {
        val methods =
            listOf("walk", "old-rod", "good-rod", "super-rod", "surf", "gift", "static", "pokeflute", "npc-trade")
        assertEquals(
            listOf(
                ObtainMethod.WALK,
                ObtainMethod.FISHING,
                ObtainMethod.FISHING,
                ObtainMethod.FISHING,
                ObtainMethod.SURF,
                ObtainMethod.GIFT,
                ObtainMethod.STATIC,
                ObtainMethod.STATIC,
                ObtainMethod.TRADE
            ),
            methods.map(ObtainMethod::fromEncounterMethod)
        )
    }

    @Test
    fun johtoMethodsAreClassified() {
        listOf("headbutt", "headbutt-low", "headbutt-normal", "headbutt-high").forEach {
            assertEquals(ObtainMethod.HEADBUTT, ObtainMethod.fromEncounterMethod(it))
        }
        assertEquals(ObtainMethod.ROCK_SMASH, ObtainMethod.fromEncounterMethod("rock-smash"))
        assertEquals(ObtainMethod.GIFT, ObtainMethod.fromEncounterMethod("gift-egg"))
        assertEquals(ObtainMethod.STATIC, ObtainMethod.fromEncounterMethod("squirt-bottle"))
        assertEquals(ObtainMethod.STATIC, ObtainMethod.fromEncounterMethod("roaming-grass"))
    }

    /** Une méthode inconnue ne doit pas disparaître des filtres. */
    @Test
    fun anUnknownMethodIsAnError() {
        val error = assertThrows(IllegalArgumentException::class.java) { ObtainMethod.fromEncounterMethod("unknown") }
        assertEquals("Méthode de rencontre inconnue : unknown", error.message)
    }
}
