package org.opensources.pokmaps.domain.pokemon

/** Contexte de combat : les Balls du Grand Marais et du Parc des Amis ne sont pas interchangeables. */
enum class CaptureEnvironment { NORMAL, GREAT_MARSH, PAL_PARK }

/** BattleScript_CalcCatchShakes, pret/pokeplatinum 1dc13dcea40c, et son équivalent Diamant/Perle. */
object Gen4CatchRate {
    fun balls(context: BallContext): List<Ball> = when (context.environment) {
        CaptureEnvironment.NORMAL -> CaptureGeneration.GEN4.balls
        CaptureEnvironment.GREAT_MARSH -> listOf(Ball.SAFARI)
        CaptureEnvironment.PAL_PARK -> listOf(Ball.PARK)
    }

    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double {
        require(rate in 1..255 && maxHp in 1..65535 && hp in 1..maxHp)
        require(context.wildLevel in 1..100 && context.elapsedTurns in 0..255 && context.safariStage in 0..12)
        require(ball in balls(context)) { "Ball indisponible dans ce contexte : $ball" }
        if (ball == Ball.MASTER || ball == Ball.PARK) return 1.0
        val speciesRate = if (ball == Ball.SAFARI) safariRate(rate, context.safariStage) else rate
        val modified = speciesRate * multiplier(ball, context) / 10
        return if (ball == Ball.SAFARI) {
            CaptureChecks.probability(modified, maxHp, maxHp, CatchStatus.NONE)
        } else {
            CaptureChecks.probability(modified, maxHp, hp, status)
        }
    }

    internal fun multiplier(ball: Ball, context: BallContext): Int = when (ball) {
        Ball.POKE, Ball.MASTER, Ball.HEAL, Ball.LUXURY, Ball.PREMIER -> 10

        Ball.GREAT, Ball.SAFARI -> 15

        Ball.ULTRA -> 20

        Ball.NET -> if (context.waterOrBug) 30 else 10

        Ball.DIVE -> if (context.waterTerrain) 35 else 10

        Ball.NEST -> (40 - context.wildLevel).coerceAtLeast(10)

        Ball.REPEAT -> if (context.alreadyCaught) 30 else 10

        Ball.TIMER -> (10 + context.elapsedTurns).coerceAtMost(40)

        Ball.DUSK -> if (context.nightOrCave) 35 else 10

        Ball.QUICK -> if (context.elapsedTurns == 0) 40 else 10

        Ball.LEVEL, Ball.LURE, Ball.MOON, Ball.FRIEND, Ball.LOVE, Ball.HEAVY, Ball.FAST,
        Ball.PARK, Ball.CHERISH -> error("Ball sans lancer ordinaire en Sinnoh : $ball")
    }

    private fun safariRate(rate: Int, stage: Int): Int =
        if (stage <= 6) rate * 10 / (40 - stage * 5) else rate * (15 + (stage - 7) * 5) / 10
}
