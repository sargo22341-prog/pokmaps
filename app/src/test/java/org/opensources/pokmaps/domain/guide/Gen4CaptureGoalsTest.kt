package org.opensources.pokmaps.domain.guide

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Gen4CaptureGoalsTest {
    @Test
    fun countersExcludeExternalContributionsAndFollowTheRegionalOfEachGame() {
        for (version in 12..14) {
            val regional = Gen4CaptureGoals.forVersion(version, national = false)
            val national = Gen4CaptureGoals.forVersion(version, national = true)
            assertEquals(if (version == 14) 181 else 132, regional.total)
            assertEquals(if (version == 14) 374 else 357, national.total)
            assertTrue(national.species.containsAll(regional.species))
            assertEquals(0, national.count(emptySet()))
            assertEquals(national.total, national.count((1..493).toSet()))
            assertFalse(
                national.species.any {
                    it in
                        setOf(65, 68, 76, 94, 377, 378, 379, 442, 486, 489, 490, 491, 492, 493)
                }
            )
        }
    }

    @Test
    fun incompatibleStartersAndPlatinumFossilsAreNeverAddedTogether() {
        for (version in 12..14) {
            val goal = Gen4CaptureGoals.forVersion(version, national = true)
            assertEquals(3, goal.count((387..395).toSet()))
            assertEquals(2, goal.count(setOf(387, 388, 390, 393)))
            assertEquals(2, goal.count((408..411).toSet()))
            // Les anciens fossiles sont renouvelables, contrairement au choix du partenaire initial.
            assertEquals(8, goal.count(setOf(138, 139, 140, 141, 345, 346, 347, 348)))
        }
        assertFalse(Gen4CaptureGoals.forVersion(12, true).species.any { it in setOf(410, 411, 484, 200, 429) })
        assertFalse(Gen4CaptureGoals.forVersion(13, true).species.any { it in setOf(408, 409, 483, 198, 430) })
        assertTrue(Gen4CaptureGoals.forVersion(14, true).species.containsAll(setOf(144, 145, 146, 483, 484)))
        assertFalse(Gen4CaptureGoals.forVersion(12, false).species.contains(479))
        assertTrue(Gen4CaptureGoals.forVersion(14, false).species.contains(479))
    }

    @Test(expected = IllegalStateException::class)
    fun otherBranchesAreRejected() {
        Gen4CaptureGoals.forVersion(11, true)
    }
}
