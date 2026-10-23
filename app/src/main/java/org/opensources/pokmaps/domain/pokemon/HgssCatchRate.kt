package org.opensources.pokmaps.domain.pokemon

/** BattleSystem_CalculateBallShakes et sMoonBallPokemon, source HGSS épinglée. */
internal object HgssCatchRate {
    val apricornBalls: List<Ball> = listOf(
        Ball.LEVEL,
        Ball.LURE,
        Ball.MOON,
        Ball.FRIEND,
        Ball.LOVE,
        Ball.HEAVY,
        Ball.FAST
    )

    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double {
        require(rate in 1..255 && maxHp in 1..65535 && hp in 1..maxHp)
        require(context.wildLevel in 1..100 && context.playerLevel in 1..100)
        require(context.elapsedTurns in 0..255 && context.safariStage in 0..12)
        require(context.weightHg >= 0 && context.baseSpeed in 0..255)
        require(context.environment != CaptureEnvironment.GREAT_MARSH)
        require(ball in Gen4CatchRate.balls(context)) { "Ball indisponible dans ce contexte : $ball" }
        if (ball == Ball.MASTER || ball == Ball.PARK) return 1.0
        val speciesRate = if (ball == Ball.SAFARI) Gen4CatchRate.safariRate(rate, context.safariStage) else rate
        val adjusted = if (ball in apricornBalls) adjustedRate(ball, speciesRate, context) else speciesRate
        val multiplier = if (ball in apricornBalls) {
            10
        } else if (ball == Ball.SPORT) {
            15
        } else {
            Gen4CatchRate.multiplier(ball, context)
        }
        // Le Safari HGSS n'a ni dégâts ni statut ; le concours conserve le combat ordinaire.
        return if (ball == Ball.SAFARI) {
            CaptureChecks.probability(adjusted * multiplier / 10, maxHp, maxHp, CatchStatus.NONE)
        } else {
            CaptureChecks.probability(adjusted * multiplier / 10, maxHp, hp, status)
        }
    }

    internal fun adjustedRate(ball: Ball, rate: Int, context: BallContext): Int {
        val adjusted = when (ball) {
            Ball.LEVEL -> rate * levelMultiplier(context.playerLevel, context.wildLevel)

            Ball.LURE -> rate * if (context.fishing) 3 else 1

            Ball.MOON -> rate * if (context.pokemonId in MOON_SPECIES) 4 else 1

            Ball.LOVE -> rate * if (context.sameSpeciesOppositeGender) 8 else 1

            Ball.FAST -> rate * if (context.baseSpeed >= 100) 4 else 1

            Ball.HEAVY -> rate + heavyBonus(context.weightHg)

            Ball.FRIEND, Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.SAFARI, Ball.MASTER,
            Ball.PARK, Ball.NET, Ball.DIVE, Ball.NEST, Ball.REPEAT, Ball.TIMER, Ball.LUXURY,
            Ball.PREMIER, Ball.DUSK, Ball.HEAL, Ball.QUICK, Ball.CHERISH, Ball.SPORT -> rate
        }
        // Le moteur ne corrige que les valeurs strictement négatives : zéro reste zéro.
        return if (adjusted < 0) 1 else adjusted.coerceAtMost(255)
    }

    private fun levelMultiplier(player: Int, wild: Int): Int = when {
        player <= wild -> 1
        player / 2 <= wild -> 2
        player / 4 <= wild -> 4
        else -> 8
    }

    private fun heavyBonus(weight: Int): Int = when {
        weight >= 4096 -> 40
        weight >= 3072 -> 30
        weight >= 2048 -> 20
        else -> -20 // Le moteur compare ici le taux à 1024 au lieu du poids.
    }

    private val MOON_SPECIES = setOf(29, 30, 31, 32, 33, 34, 173, 35, 36, 174, 39, 40, 300, 301)
}
