package org.opensources.pokmaps.domain.pokemon

/** Contexte des Balls de Johto ; la Love Ball d'Or/Argent favorise le même sexe, contrairement à son texte. */
data class BallContext(
    val pokemonId: Int,
    val weightHg: Int,
    val wildLevel: Int,
    val playerLevel: Int = 30,
    val fishing: Boolean = false,
    val sameSpeciesAndGender: Boolean = false
)

enum class CaptureGeneration {
    GEN1,
    GEN2;

    val balls: List<Ball>
        get() = when (this) {
            GEN1 -> listOf(Ball.POKE, Ball.GREAT, Ball.ULTRA, Ball.MASTER)
            GEN2 -> Ball.entries.filter { it != Ball.SAFARI }
        }

    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double =
        when (this) {
            GEN1 -> CatchRate.probability(ball, rate, maxHp, hp, status)
            GEN2 -> Gen2CatchRate.probability(ball, rate, maxHp, hp, status, context)
        }

    companion object {
        fun from(generation: Int): CaptureGeneration? = when (generation) {
            1 -> GEN1
            2 -> GEN2
            else -> null
        }
    }
}

/** Calcul entier de PokeBallEffect dans pret/pokegold, y compris les défauts du moteur d'origine. */
object Gen2CatchRate {
    fun probability(ball: Ball, rate: Int, maxHp: Int, hp: Int, status: CatchStatus, context: BallContext): Double {
        require(rate in 1..255 && hp in 1..maxHp)
        if (ball == Ball.MASTER) return 1.0
        val modified = modifiedRate(ball, rate, context)
        // La Niveau Ball saute les calculs des PV et du statut dans le jeu.
        if (ball == Ball.LEVEL) return (modified + 1) / 256.0
        var total = maxHp * 3
        var remaining = hp * 2
        if (total > 255) {
            total /= 4
            remaining = (remaining / 4).coerceAtLeast(1)
        }
        // Le moteur ne garde qu'un octet après la réduction, même au-delà de 341 PV.
        total = total and 255
        remaining = remaining and 255
        require(total != 0) { "Le moteur d'Or/Argent se bloque avec $maxHp PV maximum" }
        val factor = (total - remaining) and 255
        val value = ((modified * factor / total) and 255).coerceAtLeast(1)
        val bonus = when (status) {
            CatchStatus.SLEEP_OR_FREEZE -> 10
            CatchStatus.NONE, CatchStatus.PARALYSIS_BURN_OR_POISON -> 0
        }
        return (minOf(255, value + bonus) + 1) / 256.0
    }

    fun blocksEngine(maxHp: Int): Boolean = maxHp * 3 > 255 && (maxHp * 3 / 4 and 255) == 0

    internal fun modifiedRate(ball: Ball, rate: Int, context: BallContext): Int {
        val adjusted = when (ball) {
            Ball.POKE, Ball.MASTER, Ball.MOON, Ball.FRIEND -> rate
            Ball.GREAT, Ball.SAFARI, Ball.PARK -> rate + rate / 2
            Ball.ULTRA -> rate * 2
            Ball.LEVEL -> rate * levelMultiplier(context)
            Ball.LURE -> rate * if (context.fishing) 3 else 1
            Ball.LOVE -> rate * if (context.sameSpeciesAndGender) 8 else 1
            Ball.FAST -> rate * if (context.pokemonId in FAST_SPECIES) 4 else 1
            Ball.HEAVY -> (rate + weightBonus(context.weightHg)).let { if (it < 0) 1 else it }
        }
        return adjusted.coerceAtMost(255)
    }

    private fun levelMultiplier(context: BallContext): Int = when {
        context.playerLevel / 4 > context.wildLevel -> 8
        context.playerLevel / 2 > context.wildLevel -> 4
        context.playerLevel > context.wildLevel -> 2
        else -> 1
    }

    private fun weightBonus(weightHg: Int): Int = when {
        weightHg < 1024 -> -20
        weightHg < 2048 -> 0
        weightHg < 3072 -> 20
        weightHg < 4096 -> 30
        else -> 40
    }

    private val FAST_SPECIES = setOf(81, 88, 114)
}
