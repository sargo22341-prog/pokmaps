package org.opensources.pokmaps.domain.pokemon

import kotlin.math.pow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class Gen3CatchRateTest {
    private val context = BallContext(25, 60, 30)

    private fun probability(
        ball: Ball = Ball.POKE,
        rate: Int = 45,
        hp: Int = 100,
        status: CatchStatus = CatchStatus.NONE,
        input: BallContext = context
    ): Double = Gen3CatchRate.probability(ball, rate, 100, hp, status, input)

    @Test
    fun fourIntegerShakeChecks() {
        // Taux 45 à PV pleins : a=15, racines entières 1055 puis 32, seuil 32767.
        assertEquals((32767 / 65536.0).pow(4), probability(), 1e-12)
        // Super Ball : 45*15/10=67, a=22, seuil 36157 (et non formule continue a/255).
        assertEquals((36157 / 65536.0).pow(4), probability(Ball.GREAT), 1e-12)
    }

    @Test
    fun statusUsesIntegerMultipliers() {
        assertEquals(probability(rate = 90), probability(status = CatchStatus.SLEEP_OR_FREEZE), 0.0)
        assertEquals(probability(Ball.GREAT), probability(status = CatchStatus.PARALYSIS_BURN_OR_POISON), 0.0)
    }

    @Test
    fun guaranteedCaptureAndZeroOdds() {
        assertEquals(1.0, probability(Ball.MASTER, rate = 3), 0.0)
        assertEquals(1.0, probability(Ball.ULTRA, rate = 255, hp = 1), 0.0)
        assertEquals(0.0, probability(rate = 1), 0.0)
    }

    @Test
    fun newBallContexts() {
        assertEquals(10, Gen3CatchRate.multiplier(Ball.NET, context))
        assertEquals(30, Gen3CatchRate.multiplier(Ball.NET, context.copy(waterOrBug = true)))
        assertEquals(10, Gen3CatchRate.multiplier(Ball.DIVE, context.copy(fishing = true)))
        assertEquals(35, Gen3CatchRate.multiplier(Ball.DIVE, context.copy(underwater = true)))
        assertEquals(10, Gen3CatchRate.multiplier(Ball.REPEAT, context))
        assertEquals(30, Gen3CatchRate.multiplier(Ball.REPEAT, context.copy(alreadyCaught = true)))
        assertTrue(probability(Ball.DIVE, input = context.copy(underwater = true)) > probability(Ball.DIVE))
        assertEquals(probability(), probability(Ball.LUXURY), 0.0)
        assertEquals(probability(), probability(Ball.PREMIER), 0.0)
    }

    @Test
    fun nestAndTimerBoundaries() {
        listOf(1 to 39, 29 to 11, 30 to 10, 40 to 10, 100 to 10).forEach { (level, bonus) ->
            assertEquals(bonus, Gen3CatchRate.multiplier(Ball.NEST, context.copy(wildLevel = level)))
        }
        listOf(0 to 10, 1 to 11, 29 to 39, 30 to 40, 255 to 40).forEach { (turns, bonus) ->
            assertEquals(bonus, Gen3CatchRate.multiplier(Ball.TIMER, context.copy(elapsedTurns = turns)))
        }
    }

    @Test(expected = IllegalArgumentException::class)
    fun safariRequiresItsOwnContext() {
        probability(Ball.SAFARI)
    }

    @Test
    fun generationDispatchUsesFourShakeFormula() {
        val generation = CaptureGeneration.from(3)
        assertEquals(CaptureGeneration.GEN3, generation)
        assertEquals(
            probability(Ball.TIMER, input = context.copy(elapsedTurns = 30)),
            generation?.probability(Ball.TIMER, 45, 100, 100, CatchStatus.NONE, context.copy(elapsedTurns = 30))
        )
    }

    @Test
    fun generationAvailabilityAndWildHp() {
        assertEquals(CaptureGeneration.GEN3, CaptureGeneration.from(3))
        assertEquals(11, CaptureGeneration.GEN3.balls.size)
        assertFalse(Ball.LEVEL in CaptureGeneration.GEN3.balls)
        assertFalse(Ball.NET in CaptureGeneration.GEN2.balls)
        assertEquals(19, Gen3CatchRate.maxHp(25, 35, 5))
        assertEquals(1, Gen3CatchRate.maxHp(292, 1, 100))
    }
}
