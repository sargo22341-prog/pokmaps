package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RoamersTest {
    @Test
    fun eachGameHasItsOwnSpeciesLevelAndRoutes() {
        assertEquals(listOf(381), Roamers.pokemonIds(7))
        assertEquals(listOf(380), Roamers.pokemonIds(8))
        assertEquals(listOf(380, 381), Roamers.pokemonIds(9))
        assertEquals(listOf(243, 244), Roamers.pokemonIds(6))
        assertEquals(40, Roamers.level(4))
        assertEquals(40, Roamers.level(9))
        assertEquals(50, Roamers.level(10))
        assertEquals(RoamerArea.JOHTO, Roamers.area(6))
        assertEquals(RoamerArea.HOENN, Roamers.area(8))
        assertEquals(RoamerArea.KANTO, Roamers.area(11))
        assertEquals(emptyList<Int>(), Roamers.pokemonIds(1))
    }

    @Test
    fun remakeStarterAndEmeraldTelevisionChoiceAreExplicit() {
        assertEquals(Roamers.choices(10), Roamers.choices(11))
        assertEquals(RoamerCondition.BULBASAUR, Roamers.choices(10).single { it.pokemonId == 244 }.condition)
        assertEquals(RoamerCondition.RED, Roamers.choices(9).single { it.pokemonId == 380 }.condition)
        assertEquals(RoamerCondition.BLUE, Roamers.choices(9).single { it.pokemonId == 381 }.condition)
    }

    @Test
    fun eachBranchPresentsItsRoamersInOneArticle() {
        assertEquals("johto-roamers", Roamers.article(6))
        assertEquals("hoenn-roamers", Roamers.article(7))
        assertEquals("remake-roamers", Roamers.article(11))
        assertNull(Roamers.article(3))
    }
}
