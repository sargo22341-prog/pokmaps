package org.opensources.pokmaps.ui.map

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class WildMethodTest {
    @Test
    fun onlyWildEncountersAreDrawnOnTheMap() {
        assertEquals(WildMethod.WALK, WildMethod.from("walk"))
        assertEquals(WildMethod.SURF, WildMethod.from("surf"))
        assertEquals(WildMethod.FISHING, WildMethod.from("super-rod"))
        assertEquals(WildMethod.HEADBUTT, WildMethod.from("headbutt-high"))
        assertEquals(WildMethod.ROCK_SMASH, WildMethod.from("rock-smash"))
        assertEquals(null, WildMethod.from("gift"))
        assertEquals(null, WildMethod.from("npc-trade"))
    }

    @Test
    fun anUnknownMethodIsAnError() {
        assertThrows(IllegalArgumentException::class.java) { WildMethod.from("unknown") }
    }
}
