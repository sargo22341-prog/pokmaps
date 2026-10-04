package org.opensources.pokmaps.domain.pokemon

import kotlin.math.ceil
import kotlin.math.max
import kotlin.math.min

/** Poké Balls de la 1re génération et leurs paramètres dans la formule de capture. */
enum class Ball(val itemIdentifier: String, val randomMax: Int, val hpDivisor: Int) {
    POKE("poke-ball", randomMax = 255, hpDivisor = 12),
    GREAT("great-ball", randomMax = 200, hpDivisor = 8),
    ULTRA("ultra-ball", randomMax = 150, hpDivisor = 12),
    SAFARI("safari-ball", randomMax = 150, hpDivisor = 12),
    MASTER("master-ball", randomMax = 0, hpDivisor = 0)
}

/** Statut du Pokémon sauvage : sommeil et gel facilitent le plus la capture. */
enum class CatchStatus(val bonus: Int) {
    NONE(0),
    SLEEP_OR_FREEZE(25),
    PARALYSIS_BURN_OR_POISON(12)
}

/**
 * Formule de capture de la 1re génération (Rouge, Bleu, Jaune) :
 * 1. la Master Ball capture toujours ;
 * 2. R1 est tiré entre 0 et 255 (Poké Ball), 200 (Super Ball) ou 150 (Hyper Ball, Safari Ball) ;
 *    le Pokémon est capturé si R1 < S (25 endormi ou gelé, 12 paralysé, brûlé ou empoisonné) ;
 * 3. sinon la capture échoue si R1 − S > taux de capture ;
 * 4. sinon f = ⌊⌊PVmax × 255 / B⌋ / max(1, ⌊PV / 4⌋)⌋ (B = 8 pour la Super Ball, 12 sinon), plafonné à 255,
 *    et le Pokémon est capturé si R2 (entre 0 et 255) ≤ f.
 */
object CatchRate {
    fun probability(ball: Ball, captureRate: Int, maxHp: Int, currentHp: Int, status: CatchStatus): Double {
        if (ball == Ball.MASTER) return 1.0
        val draws = ball.randomMax + 1
        val bonus = min(status.bonus, draws)
        val reachesHpCheck = min(captureRate + 1, draws - bonus).coerceAtLeast(0)
        val f = min(MAX_F, (maxHp * MAX_F / ball.hpDivisor) / max(1, currentHp / 4))
        return bonus.toDouble() / draws + reachesHpCheck.toDouble() / draws * (f + 1) / (MAX_F + 1)
    }

    /**
     * PV max d'un Pokémon sauvage (sans points d'effort) : ⌊((base + DV) × 2) × niveau / 100⌋ + niveau + 10.
     * Le DV des PV d'un Pokémon sauvage est aléatoire (0 à 15) : on prend une valeur moyenne.
     */
    fun maxHp(baseHp: Int, level: Int, dv: Int = AVERAGE_DV): Int = (baseHp + dv) * 2 * level / 100 + level + 10

    /** PV restants pour une fraction des PV max (au moins 1 PV). */
    fun currentHp(maxHp: Int, fraction: Double): Int = max(1, ceil(maxHp * fraction).toInt())

    /** Meilleure balle hors Master Ball (la Safari Ball seulement dans le Parc Safari). */
    fun bestBall(probabilities: Map<Ball, Double>): Ball? = probabilities
        .filterKeys { it != Ball.MASTER }
        .maxWithOrNull(compareBy<Map.Entry<Ball, Double>> { it.value }.thenBy { -it.key.ordinal })
        ?.key

    private const val MAX_F = 255
    const val AVERAGE_DV = 8
}
