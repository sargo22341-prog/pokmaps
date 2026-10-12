package org.opensources.pokmaps.domain.hoenn

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PokeblockTest {
    private val cheri = Berry("cheri-berry", "Baie Ceriz", 3, 2, 3, 25, listOf(10, 0, 0, 0, 0))
    private val chesto = Berry("chesto-berry", "Baie Maron", 3, 2, 3, 25, listOf(0, 10, 0, 0, 0))

    @Test
    fun dryRecipeSubtractsNegativeFlavorBeforeSpeedBonus() {
        assertEquals(Pokeblock.Recipe(listOf(0, 9, 0, 0, 0), 23), blendPokeblock(listOf(cheri, chesto)))
        assertEquals(Pokeblock.Recipe(listOf(0, 12, 0, 0, 0), 23), blendPokeblock(listOf(cheri, chesto), 10_000))
    }

    @Test
    fun identicalBerriesMakeBlackBlocksWithUnpredictableFlavors() {
        assertEquals(Pokeblock.Black(23), blendPokeblock(listOf(cheri, cheri)))
    }

    @Test
    fun balancedFlavorsAlsoMakeBlackBlocks() {
        val balanced = cheri.copy(identifier = "oran-berry", smoothness = 20, flavors = List(5) { 10 })
        assertEquals(Pokeblock.Black(18), blendPokeblock(listOf(balanced, balanced.copy(identifier = "other"))))
    }

    @Test
    fun fourParticipantsUseIntegerMeanAndClampFeelAndFlavors() {
        val berries = List(4) { cheri.copy(identifier = "berry-$it", smoothness = 0, flavors = listOf(40, 0, 0, 0, 0)) }
        val result = blendPokeblock(berries, 65535)
        assertEquals(Pokeblock.Recipe(listOf(255, 0, 0, 0, 0), 0), result)
    }

    @Test(expected = IllegalArgumentException::class)
    fun oneParticipantIsRejected() {
        blendPokeblock(listOf(cheri))
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidBerryIsRejected() {
        assertTrue(cheri.copy(flavors = listOf(-1, 0, 0, 0, 0)).name.isNotEmpty())
    }
}
