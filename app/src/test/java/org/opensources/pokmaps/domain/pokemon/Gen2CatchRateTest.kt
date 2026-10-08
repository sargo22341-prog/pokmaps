package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class Gen2CatchRateTest {
    private val context = BallContext(25, 60, 10)

    private fun probability(ball: Ball, hp: Int = 100, status: CatchStatus = CatchStatus.NONE): Double =
        Gen2CatchRate.probability(ball, 45, 100, hp, status, context)

    @Test
    fun integerHpFormulaAndStatusMatchGoldSilver() {
        assertEquals(16 / 256.0, probability(Ball.POKE), 0.0)
        assertEquals(23 / 256.0, probability(Ball.GREAT), 0.0)
        assertEquals(31 / 256.0, probability(Ball.ULTRA), 0.0)
        assertEquals(26 / 256.0, probability(Ball.POKE, status = CatchStatus.SLEEP_OR_FREEZE), 0.0)
        assertEquals(probability(Ball.POKE), probability(Ball.POKE, status = CatchStatus.PARALYSIS_BURN_OR_POISON), 0.0)
        assertEquals(45 / 256.0, probability(Ball.POKE, hp = 1), 0.0)
        assertEquals(1.0, probability(Ball.MASTER), 0.0)
    }

    @Test
    fun levelBallIgnoresHpAndStatusAndUsesStrictIntegerThresholds() {
        assertEquals(181 / 256.0, probability(Ball.LEVEL), 0.0)
        assertEquals(probability(Ball.LEVEL), probability(Ball.LEVEL, 1, CatchStatus.SLEEP_OR_FREEZE), 0.0)
        assertEquals(90, Gen2CatchRate.modifiedRate(Ball.LEVEL, 45, context.copy(playerLevel = 20)))
        assertEquals(90, Gen2CatchRate.modifiedRate(Ball.LEVEL, 45, context.copy(playerLevel = 21)))
        assertEquals(180, Gen2CatchRate.modifiedRate(Ball.LEVEL, 45, context.copy(playerLevel = 22)))
        assertEquals(180, Gen2CatchRate.modifiedRate(Ball.LEVEL, 45, context.copy(playerLevel = 40)))
        assertEquals(255, Gen2CatchRate.modifiedRate(Ball.LEVEL, 45, context.copy(playerLevel = 44)))
    }

    @Test
    fun apricornBallsReproduceTheOriginalEffectsAndBugs() {
        assertEquals(45, Gen2CatchRate.modifiedRate(Ball.MOON, 45, context))
        assertEquals(45, Gen2CatchRate.modifiedRate(Ball.FRIEND, 45, context))
        assertEquals(135, Gen2CatchRate.modifiedRate(Ball.LURE, 45, context.copy(fishing = true)))
        assertEquals(45, Gen2CatchRate.modifiedRate(Ball.LURE, 45, context))
        assertEquals(255, Gen2CatchRate.modifiedRate(Ball.LOVE, 45, context.copy(sameSpeciesAndGender = true)))
        listOf(81, 88, 114).forEach {
            assertEquals(180, Gen2CatchRate.modifiedRate(Ball.FAST, 45, context.copy(pokemonId = it)))
        }
        assertEquals(45, Gen2CatchRate.modifiedRate(Ball.FAST, 45, context.copy(pokemonId = 243)))
        assertEquals(25, Gen2CatchRate.modifiedRate(Ball.HEAVY, 45, context))
        assertEquals(1, Gen2CatchRate.modifiedRate(Ball.HEAVY, 3, context))
        assertEquals(75, Gen2CatchRate.modifiedRate(Ball.HEAVY, 45, context.copy(weightHg = 4095)))
        assertEquals(85, Gen2CatchRate.modifiedRate(Ball.HEAVY, 45, context.copy(weightHg = 4096)))
        assertEquals(67, Gen2CatchRate.modifiedRate(Ball.PARK, 45, context))
    }

    @Test
    fun highHpOverflowIsReproducedAndTheEngineHangIsReported() {
        assertEquals(103 / 256.0, Gen2CatchRate.probability(Ball.POKE, 45, 400, 400, CatchStatus.NONE, context), 0.0)
        assertThrows(IllegalArgumentException::class.java) {
            Gen2CatchRate.probability(Ball.POKE, 45, 342, 342, CatchStatus.NONE, context)
        }
    }
}
