package org.opensources.pokmaps.domain.pokemon

import kotlin.math.pow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class Gen4CatchRateTest {
    private val context = BallContext(25, 60, 30)

    private fun probability(ball: Ball, input: BallContext = context, rate: Int = 45): Double =
        CaptureGeneration.GEN4.probability(ball, rate, 100, 100, CatchStatus.NONE, input)

    @Test
    fun integerFormulaAndStatus() {
        assertEquals((32767 / 65536.0).pow(4), probability(Ball.POKE), 1e-12)
        assertEquals(probability(Ball.POKE), probability(Ball.HEAL), 0.0)
        assertEquals(1.0, probability(Ball.MASTER), 0.0)
        assertEquals(0.0, probability(Ball.POKE, rate = 1), 0.0)
        assertEquals(
            probability(Ball.POKE, rate = 90),
            Gen4CatchRate.probability(Ball.POKE, 45, 100, 100, CatchStatus.SLEEP_OR_FREEZE, context),
            0.0
        )
    }

    @Test
    fun quickAndDuskUseTheirDsContexts() {
        assertEquals(40, Gen4CatchRate.multiplier(Ball.QUICK, context))
        assertEquals(10, Gen4CatchRate.multiplier(Ball.QUICK, context.copy(elapsedTurns = 1)))
        assertEquals(35, Gen4CatchRate.multiplier(Ball.DUSK, context.copy(nightOrCave = true)))
        assertEquals(10, Gen4CatchRate.multiplier(Ball.DUSK, context))
        assertEquals(35, Gen4CatchRate.multiplier(Ball.DIVE, context.copy(waterTerrain = true)))
        assertEquals(10, Gen4CatchRate.multiplier(Ball.DIVE, context.copy(underwater = true)))
        assertTrue(probability(Ball.QUICK) > probability(Ball.POKE))
    }

    @Test
    fun safariStageAndPalParkAreSeparateContexts() {
        val marsh = context.copy(environment = CaptureEnvironment.GREAT_MARSH)
        assertEquals(listOf(Ball.SAFARI), Gen4CatchRate.balls(marsh))
        assertEquals(probability(Ball.GREAT), probability(Ball.SAFARI, marsh), 0.0)
        assertTrue(probability(Ball.SAFARI, marsh.copy(safariStage = 12)) > probability(Ball.SAFARI, marsh))
        assertTrue(probability(Ball.SAFARI, marsh.copy(safariStage = 0)) < probability(Ball.SAFARI, marsh))
        assertEquals(
            probability(Ball.SAFARI, marsh),
            Gen4CatchRate.probability(Ball.SAFARI, 45, 100, 1, CatchStatus.SLEEP_OR_FREEZE, marsh),
            0.0
        )
        val park = context.copy(environment = CaptureEnvironment.PAL_PARK)
        assertEquals(listOf(Ball.PARK), Gen4CatchRate.balls(park))
        assertEquals(1.0, probability(Ball.PARK, park), 0.0)
        listOf(Ball.SAFARI, Ball.PARK, Ball.CHERISH).forEach { ball ->
            assertThrows(IllegalArgumentException::class.java) { probability(ball) }
        }
        assertFalse(Ball.CHERISH in CaptureGeneration.GEN4.balls)
    }
}
