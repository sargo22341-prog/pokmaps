package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opensources.pokmaps.domain.model.VersionGroup

class HgssCatchRateTest {
    private val context = BallContext(25, 60, 10, versionGroup = VersionGroup.HEARTGOLD_SOULSILVER)

    @Test
    fun levelUsesIntegerDivisionAndStrictBoundaries() {
        val cases = mapOf(10 to 10, 11 to 20, 21 to 20, 22 to 40, 43 to 40, 44 to 80)
        cases.forEach { (player, expected) ->
            assertEquals(expected, HgssCatchRate.adjustedRate(Ball.LEVEL, 10, context.copy(playerLevel = player)))
        }
        assertEquals(255, HgssCatchRate.adjustedRate(Ball.LEVEL, 100, context.copy(playerLevel = 100)))
    }

    @Test
    fun heavyUsesHgssBugAndKeepsZeroDistinctFromNegative() {
        val cases = mapOf(
            1023 to 25,
            1024 to 25,
            2047 to 25,
            2048 to 65,
            3071 to 65,
            3072 to 75,
            4095 to 75,
            4096 to 85
        )
        cases.forEach { (weight, expected) ->
            assertEquals(expected, HgssCatchRate.adjustedRate(Ball.HEAVY, 45, context.copy(weightHg = weight)))
        }
        assertEquals(0, HgssCatchRate.adjustedRate(Ball.HEAVY, 20, context))
        assertEquals(1, HgssCatchRate.adjustedRate(Ball.HEAVY, 19, context))
        assertEquals(255, HgssCatchRate.adjustedRate(Ball.HEAVY, 250, context.copy(weightHg = 4096)))
        assertEquals(45, Gen2CatchRate.modifiedRate(Ball.HEAVY, 45, context.copy(weightHg = 1024)))
    }

    @Test
    fun apricornConditionsDoNotBorrowGscBugs() {
        assertEquals(10, HgssCatchRate.adjustedRate(Ball.FAST, 10, context.copy(baseSpeed = 99)))
        assertEquals(40, HgssCatchRate.adjustedRate(Ball.FAST, 10, context.copy(baseSpeed = 100)))
        assertEquals(30, HgssCatchRate.adjustedRate(Ball.LURE, 10, context.copy(fishing = true)))
        assertEquals(10, HgssCatchRate.adjustedRate(Ball.LURE, 10, context))
        assertEquals(10, HgssCatchRate.adjustedRate(Ball.LOVE, 10, context.copy(sameSpeciesAndGender = true)))
        assertEquals(80, HgssCatchRate.adjustedRate(Ball.LOVE, 10, context.copy(sameSpeciesOppositeGender = true)))
        listOf(29, 30, 31, 32, 33, 34, 173, 35, 36, 174, 39, 40, 300, 301).forEach { id ->
            assertEquals(40, HgssCatchRate.adjustedRate(Ball.MOON, 10, context.copy(pokemonId = id)))
        }
        assertEquals(10, HgssCatchRate.adjustedRate(Ball.MOON, 10, context.copy(pokemonId = 133)))
        assertEquals(10, HgssCatchRate.adjustedRate(Ball.FRIEND, 10, context))
    }

    @Test
    fun ordinaryDsBallsKeepSinnohResults() {
        val sinnoh = context.copy(versionGroup = VersionGroup.PLATINUM)
        CaptureGeneration.GEN4.balls.forEach { ball ->
            assertEquals(probability(ball, sinnoh), probability(ball, context), 0.0)
        }
        assertFalse(Ball.CHERISH in Gen4CatchRate.balls(context))
        assertThrows(IllegalArgumentException::class.java) { probability(Ball.SPORT, context) }
        assertThrows(IllegalArgumentException::class.java) { probability(Ball.FAST, sinnoh) }
    }

    @Test
    fun environmentsHaveExclusiveBallsAndCombatRules() {
        val safari = context.copy(environment = CaptureEnvironment.HGSS_SAFARI)
        val contest = context.copy(environment = CaptureEnvironment.BUG_CONTEST)
        assertEquals(listOf(Ball.SAFARI), Gen4CatchRate.balls(safari))
        assertEquals(listOf(Ball.SPORT), Gen4CatchRate.balls(contest))
        assertEquals(
            1.0,
            Gen4CatchRate.probability(
                Ball.SAFARI,
                255,
                100,
                100,
                CatchStatus.NONE,
                safari.copy(safariStage = 12)
            ),
            0.0
        )
        assertEquals(
            probability(Ball.SAFARI, safari),
            Gen4CatchRate.probability(Ball.SAFARI, 45, 100, 1, CatchStatus.SLEEP_OR_FREEZE, safari),
            0.0
        )
        assertTrue(
            Gen4CatchRate.probability(Ball.SPORT, 45, 100, 1, CatchStatus.SLEEP_OR_FREEZE, contest) >
                probability(Ball.SPORT, contest)
        )
        assertEquals(1.0, probability(Ball.PARK, context.copy(environment = CaptureEnvironment.PAL_PARK)), 0.0)
        assertThrows(IllegalArgumentException::class.java) {
            probability(Ball.SAFARI, context.copy(environment = CaptureEnvironment.GREAT_MARSH))
        }
        assertThrows(IllegalArgumentException::class.java) {
            probability(Ball.SPORT, contest.copy(versionGroup = VersionGroup.PLATINUM))
        }
    }

    @Test
    fun invalidInputsAreRejected() {
        listOf(
            context.copy(playerLevel = 0),
            context.copy(wildLevel = 101),
            context.copy(baseSpeed = 256),
            context.copy(weightHg = -1),
            context.copy(elapsedTurns = 256),
            context.copy(safariStage = 13)
        ).forEach { input ->
            assertThrows(IllegalArgumentException::class.java) { probability(Ball.POKE, input) }
        }
    }

    private fun probability(ball: Ball, input: BallContext): Double =
        Gen4CatchRate.probability(ball, 45, 100, 100, CatchStatus.NONE, input)
}
