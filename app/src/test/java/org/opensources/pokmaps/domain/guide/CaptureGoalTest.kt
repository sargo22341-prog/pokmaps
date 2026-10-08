package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Test

class CaptureGoalTest {
    @Test
    fun eachOfficialCollectionHasItsActualTarget() {
        val expected = mapOf(4425 to 124, 540348 to 124, 4450 to 129, 5090 to 199, 5120 to 199, 5954 to 206)
        for ((id, total) in expected) {
            val goal = requireNotNull(CaptureGoals.forAchievement(id))
            assertEquals(total, goal.total)
            assertEquals(total, goal.count((1..251).toSet()))
            assertEquals(0, goal.count(emptySet()))
        }
    }

    @Test
    fun differentStarterFamiliesCannotBeAddedTogetherAndMewDoesNotCount() {
        val goal = requireNotNull(CaptureGoals.forAchievement(4425))
        assertEquals(1, goal.count(setOf(1, 4, 7, 151)))
        assertEquals(3, goal.count(setOf(1, 2, 3, 4, 7, 151)))
    }

    @Test
    fun goldAndSilverCountOnlyOneEvolutionPerFiniteElementalStone() {
        val goal = requireNotNull(CaptureGoals.forAchievement(5090))
        assertEquals(1, goal.count(setOf(62, 91, 121, 134)))
        assertEquals(1, goal.count(setOf(26, 135)))
        assertEquals(1, goal.count(setOf(45, 71, 103)))
    }

    @Test
    fun crystalStonesAllowEveryEvolutionButExcludeEventCelebi() {
        val goal = requireNotNull(CaptureGoals.forAchievement(5954))
        assertEquals(4, goal.count(setOf(62, 91, 121, 134, 251)))
    }
}
