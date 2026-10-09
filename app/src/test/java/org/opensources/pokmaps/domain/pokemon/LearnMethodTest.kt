package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class LearnMethodTest {
    @Test
    fun everyMethodOfTheDatabaseHasItsTab() {
        assertEquals(LearnMethod.EGG, LearnMethod.from("egg"))
        assertEquals(MoveTab.EGG to MoveNote.LIGHT_BALL_PARENT, LearnMethod.LIGHT_BALL_EGG.let { it.tab to it.note })
        assertEquals(MoveTab.TUTOR, LearnMethod.from("stadium-surfing-pikachu").tab)
    }

    @Test
    fun anUnknownMethodIsAnError() {
        assertThrows(IllegalStateException::class.java) { LearnMethod.from("xd-shadow") }
    }

    @Test
    fun evolutionTriggersAndStatisticsAreClosedSets() {
        assertEquals(EvolutionTrigger.SHED, EvolutionTrigger.from("shed"))
        assertThrows(IllegalStateException::class.java) { EvolutionTrigger.from("spin") }
        assertEquals(RelativeStats.DEFENSE_HIGHER, RelativeStats.from(-1))
        assertThrows(IllegalStateException::class.java) { RelativeStats.from(2) }
    }
}
