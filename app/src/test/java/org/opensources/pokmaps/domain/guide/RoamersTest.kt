package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RoamersTest {
    @Test
    fun eachGameHasItsOwnSpeciesAndRoutes() {
        assertEquals(setOf(381), Roamers.pokemonIds(7))
        assertEquals(setOf(380), Roamers.pokemonIds(8))
        assertEquals(setOf(380, 381), Roamers.pokemonIds(9))
        assertEquals(setOf(243, 244), Roamers.pokemonIds(6))
        assertEquals(20, Roamers.places(9).size)
        assertEquals(25, Roamers.places(10).size)
        assertTrue(Roamers.valid(9, RoamerObservation(380, "route134")))
        assertFalse(Roamers.valid(9, RoamerObservation(380, "route112")))
        assertFalse(Roamers.valid(7, RoamerObservation(380, "route110")))
        assertFalse(Roamers.valid(10, RoamerObservation(243, "route21-south")))
        assertTrue(Roamers.valid(10, RoamerObservation(243, "route21-north")))
        assertTrue(Roamers.places(1).isEmpty())
    }

    @Test
    fun remakeStarterAndEmeraldTelevisionChoiceAreExplicit() {
        assertEquals(244, Roamers.forStarter(1))
        assertEquals(245, Roamers.forStarter(4))
        assertEquals(243, Roamers.forStarter(7))
        assertEquals(Roamers.choices(10), Roamers.choices(11))
        assertEquals(RoamerCondition.RED, Roamers.choices(9).single { it.pokemonId == 380 }.condition)
        assertEquals(RoamerCondition.BLUE, Roamers.choices(9).single { it.pokemonId == 381 }.condition)
    }

    @Test(expected = IllegalArgumentException::class)
    fun twoMutuallyExclusiveGbaRoamersCannotBeImported() {
        validateGuideProgress(
            9,
            GuideProgress(
                roamers = listOf(
                    RoamerObservation(380, "route110"),
                    RoamerObservation(381, "route134")
                )
            )
        )
    }
}
