package org.opensources.pokmaps.domain.pokemon

import kotlin.math.pow
import kotlin.math.sqrt

/** Calcul entier des quatre contrôles de capture des moteurs GBA pret, hors Parc Safari. */
object Gen3CatchRate {
    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double {
        require(rate in 1..255 && maxHp in 1..MAX_HP && hp in 1..maxHp)
        require(context.wildLevel in 1..100 && context.elapsedTurns in 0..255)
        require(ball in CaptureGeneration.GEN3.balls)
        if (ball == Ball.MASTER) return 1.0
        val modified = rate * multiplier(ball, context) / 10
        val value = modified * (3 * maxHp - 2 * hp) / (3 * maxHp)
        val odds = when (status) {
            CatchStatus.NONE -> value
            CatchStatus.SLEEP_OR_FREEZE -> value * 2
            CatchStatus.PARALYSIS_BURN_OR_POISON -> value * 15 / 10
        }
        if (odds >= 255) return 1.0
        if (odds == 0) return 0.0
        val root = sqrt(sqrt((SHAKE_NUMERATOR / odds).toDouble()).toInt().toDouble()).toInt()
        val threshold = SHAKE_SCALE / root
        return (threshold / RANDOM_RANGE).pow(4)
    }

    /** PV sauvages sans EV, avec un IV moyen de 15 ; Munja n'a toujours qu'un PV. */
    fun maxHp(pokemonId: Int, baseHp: Int, level: Int): Int {
        require(baseHp in 1..255 && level in 1..100)
        return if (pokemonId == 292) 1 else (2 * baseHp + AVERAGE_IV) * level / 100 + level + 10
    }

    internal fun multiplier(ball: Ball, context: BallContext): Int = when (ball) {
        Ball.POKE, Ball.MASTER, Ball.LUXURY, Ball.PREMIER -> 10

        Ball.GREAT -> 15

        Ball.ULTRA -> 20

        Ball.NET -> if (context.waterOrBug) 30 else 10

        Ball.DIVE -> if (context.underwater) 35 else 10

        Ball.NEST -> (40 - context.wildLevel).coerceAtLeast(10)

        Ball.REPEAT -> if (context.alreadyCaught) 30 else 10

        Ball.TIMER -> (context.elapsedTurns + 10).coerceAtMost(40)

        Ball.SAFARI, Ball.LEVEL, Ball.LURE, Ball.MOON, Ball.FRIEND, Ball.LOVE, Ball.HEAVY, Ball.FAST, Ball.PARK ->
            error("Ball indisponible en génération 3 : $ball")
    }

    private const val AVERAGE_IV = 15

    // Le moteur stocke les PV sur 16 bits ; cette borne garde aussi les produits dans un Int.
    private const val MAX_HP = 65535

    private const val SHAKE_NUMERATOR = 16711680
    private const val SHAKE_SCALE = 1048560
    private const val RANDOM_RANGE = 65536.0
}
