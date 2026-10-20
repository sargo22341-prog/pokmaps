package org.opensources.pokmaps.domain.sinnoh

import org.junit.Assert.assertEquals
import org.junit.Test

class SinnohBerryTest {
    private val cheri = SinnohBerry("cheri-berry", "Baie Ceriz", 3, 5, 15, 25, listOf(10, 0, 0, 0, 0))

    @Test
    fun mulchUsesTheEngineIntegerRounding() {
        assertEquals(180, cheri.stageMinutes(Mulch.NONE))
        assertEquals(135, cheri.stageMinutes(Mulch.GROWTH))
        assertEquals(270, cheri.stageMinutes(Mulch.DAMP))
        assertEquals(180, cheri.stageMinutes(Mulch.STABLE))
        assertEquals(180, cheri.stageMinutes(Mulch.GOOEY))
        assertEquals(15, cheri.hourlyDrain(Mulch.NONE))
        assertEquals(22, cheri.hourlyDrain(Mulch.GROWTH))
        assertEquals(7, cheri.hourlyDrain(Mulch.DAMP))
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidPoffinFlavorVectorIsRejected() {
        cheri.copy(flavors = listOf(10))
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidUndergroundPriceCannotBecomeAValidOffer() {
        UndergroundPrice(3, 10, 10)
    }
}
