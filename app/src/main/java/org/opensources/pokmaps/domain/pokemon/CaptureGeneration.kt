package org.opensources.pokmaps.domain.pokemon

import org.opensources.pokmaps.domain.model.Generation

/** Contexte des Balls de Johto et des jeux GBA. */
data class BallContext(
    val pokemonId: Int,
    val weightHg: Int,
    val wildLevel: Int,
    val playerLevel: Int = 30,
    val fishing: Boolean = false,
    val sameSpeciesAndGender: Boolean = false,
    val underwater: Boolean = false,
    val elapsedTurns: Int = 0,
    val alreadyCaught: Boolean = false,
    val waterOrBug: Boolean = false
)

enum class CaptureGeneration {
    GEN1,
    GEN2,
    GEN3;

    val balls: List<Ball>
        get() = when (this) {
            GEN1 -> listOf(Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.MASTER)

            GEN2 -> listOf(
                Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.MASTER, Ball.LEVEL, Ball.LURE, Ball.MOON,
                Ball.FRIEND, Ball.LOVE, Ball.HEAVY, Ball.FAST, Ball.PARK
            )

            GEN3 -> listOf(
                Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.MASTER, Ball.NET, Ball.DIVE, Ball.NEST,
                Ball.REPEAT, Ball.TIMER, Ball.LUXURY, Ball.PREMIER
            )
        }

    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double =
        when (this) {
            GEN1 -> CatchRate.probability(ball, rate, maxHp, hp, status)
            GEN2 -> Gen2CatchRate.probability(ball, rate, maxHp, hp, status, context)
            GEN3 -> Gen3CatchRate.probability(ball, rate, maxHp, hp, status, context)
        }

    companion object {
        fun from(generation: Int): CaptureGeneration? = when (Generation.of(generation)) {
            Generation.GEN1 -> GEN1
            Generation.GEN2 -> GEN2
            Generation.GEN3 -> GEN3
        }
    }
}
