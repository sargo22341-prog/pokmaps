package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Test

class CatchRateTest {
    private fun probability(ball: Ball, rate: Int, hp: Int = 100, status: CatchStatus = CatchStatus.NONE) =
        CatchRate.probability(ball, rate, maxHp = 100, currentHp = hp, status = status)

    @Test
    fun masterBallAlwaysCatches() {
        assertEquals(1.0, probability(Ball.MASTER, rate = 3), 0.0)
    }

    @Test
    fun fullHpWithoutStatus() {
        // f = ⌊⌊100 × 255 / 12⌋ / 25⌋ = 85 ; P = 46/256 × 86/256
        assertEquals(46.0 / 256 * 86 / 256, probability(Ball.POKE, rate = 45), 1e-9)
        // Super Ball : f = ⌊3187 / 25⌋ = 127 ; P = 46/201 × 128/256
        assertEquals(46.0 / 201 * 128 / 256, probability(Ball.GREAT, rate = 45), 1e-9)
        assertEquals(46.0 / 151 * 86 / 256, probability(Ball.ULTRA, rate = 45), 1e-9)
    }

    @Test
    fun superBallBeatsHyperBallAtFullHealth() {
        val probabilities = Ball.entries.associateWith { probability(it, rate = 45) } - Ball.SAFARI
        assertEquals(Ball.GREAT, CatchRate.bestBall(probabilities))
    }

    @Test
    fun statusAddsGuaranteedDraws() {
        // Endormi : 25 tirages sur 151 capturent d'office, puis 4 tirages passent au test des PV.
        assertEquals(
            25.0 / 151 + 4.0 / 151 * 86 / 256,
            probability(Ball.ULTRA, rate = 3, status = CatchStatus.SLEEP_OR_FREEZE),
            1e-9
        )
    }

    @Test
    fun oneHpMaximisesF() {
        assertEquals(46.0 / 256, probability(Ball.POKE, rate = 45, hp = 1), 1e-9)
    }

    @Test
    fun highCaptureRateIsCappedByDraws() {
        assertEquals(1.0 * 86 / 256, probability(Ball.POKE, rate = 255), 1e-9)
    }

    @Test
    fun wildMaxHp() {
        // Pikachu (35 PV de base) niveau 5 : ⌊(35 + 8) × 2 × 5 / 100⌋ + 5 + 10
        assertEquals(19, CatchRate.maxHp(baseHp = 35, level = 5))
        assertEquals(1, CatchRate.currentHp(19, 0.0))
        assertEquals(10, CatchRate.currentHp(19, 0.5))
    }
}
