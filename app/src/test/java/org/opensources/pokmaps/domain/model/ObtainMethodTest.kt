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

    /** Une méthode d'un nouveau jeu (ex. Coup d'Boule dans Or/Argent) ne doit pas disparaître des filtres. */
    @Test
    fun anUnknownMethodIsAnError() {
        val error = assertThrows(IllegalArgumentException::class.java) { ObtainMethod.fromEncounterMethod("headbutt") }
        assertEquals("Méthode de rencontre inconnue : headbutt", error.message)
    }
}
