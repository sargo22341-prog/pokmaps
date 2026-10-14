package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Gen3CaptureGoalsTest {
    @Test
    fun officialTargetsAndSapphireCollectionMatchTheirOwnRules() {
        val expected = mapOf(7 to 177, 8 to 178, 9 to 212, 10 to 170, 11 to 171)
        for ((version, total) in expected) {
            val goal = Gen3CaptureGoals.forVersion(version)
            assertEquals(total, goal.total)
            assertEquals(total, goal.count((1..386).toSet()))
            assertEquals(0, goal.count(emptySet()))
            assertFalse(goal.species.any { it in setOf(151, 249, 250, 251, 385, 386) })
        }
        assertEquals(177, CaptureGoals.forAchievement(91998)?.total)
        assertEquals(212, CaptureGoals.forAchievement(57275)?.total)
        assertEquals(170, CaptureGoals.forAchievement(33625)?.total)
        assertEquals(171, CaptureGoals.forAchievement(34809)?.total)
    }

    @Test
    fun startersFossilsAndFiniteMoonStoneCannotBeCountedTwice() {
        val ruby = Gen3CaptureGoals.forVersion(7)
        assertEquals(3, ruby.count(setOf(252, 253, 254, 255, 258)))
        assertEquals(2, ruby.count(setOf(345, 346, 347)))
        assertEquals(1, ruby.count(setOf(40, 301)))
        assertEquals(2, Gen3CaptureGoals.forVersion(8).count(setOf(40, 301)))
        assertEquals(4, Gen3CaptureGoals.forVersion(9).count(setOf(345, 346, 347, 348)))
        assertFalse(Gen3CaptureGoals.forVersion(9).species.any { it in 152..160 })
        assertEquals(1, Gen3CaptureGoals.forVersion(9).count(setOf(380, 381)))
    }

    @Test
    fun remakeStarterAndRoamerAreOneCorrelatedChoice() {
        val goal = Gen3CaptureGoals.forVersion(10)
        assertEquals(4, goal.count(setOf(1, 2, 3, 244)))
        assertEquals(3, goal.count(setOf(1, 2, 3, 245)))
        assertEquals(4, goal.count(setOf(4, 5, 6, 245, 243)))
        assertEquals(4, goal.count(setOf(106, 107, 236, 237)))
        assertFalse(goal.species.any { it in setOf(196, 197, 199, 208, 212, 230, 233) })
    }
}
