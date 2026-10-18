package org.opensources.pokmaps.domain.pokemon

/** Calcul entier des quatre contrôles de capture des moteurs GBA pret, hors Parc Safari. */
object Gen3CatchRate {
    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double {
        require(rate in 1..255 && maxHp in 1..MAX_HP && hp in 1..maxHp)
        require(context.wildLevel in 1..100 && context.elapsedTurns in 0..255)
        require(ball in CaptureGeneration.GEN3.balls)
        if (ball == Ball.MASTER) return 1.0
        val modified = rate * multiplier(ball, context) / 10
        return CaptureChecks.probability(modified, maxHp, hp, status)
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

        Ball.DUSK, Ball.HEAL, Ball.QUICK, Ball.CHERISH,
        Ball.SAFARI, Ball.LEVEL, Ball.LURE, Ball.MOON, Ball.FRIEND, Ball.LOVE, Ball.HEAVY, Ball.FAST, Ball.PARK ->
            error("Ball indisponible en génération 3 : $ball")
    }

    private const val AVERAGE_IV = 15

    // Le moteur stocke les PV sur 16 bits ; cette borne garde aussi les produits dans un Int.
    private const val MAX_HP = 65535
}
