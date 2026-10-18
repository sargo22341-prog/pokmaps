package org.opensources.pokmaps.domain.pokemon

import kotlin.math.pow
import kotlin.math.sqrt

/** Contrôles entiers communs aux moteurs GBA et DS. */
internal object CaptureChecks {
    fun probability(modifiedRate: Int, maxHp: Int, hp: Int, status: CatchStatus): Double {
        val value = modifiedRate * (3 * maxHp - 2 * hp) / (3 * maxHp)
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

    private const val SHAKE_NUMERATOR = 16711680
    private const val SHAKE_SCALE = 1048560
    private const val RANDOM_RANGE = 65536.0
}
