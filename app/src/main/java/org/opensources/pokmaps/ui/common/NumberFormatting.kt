package org.opensources.pokmaps.ui.common

import java.text.NumberFormat
import java.util.Locale

private val FRENCH = Locale.FRANCE

/** Nombre à la française, avec au plus `decimals` décimales (« 12,5 »). */
fun formatNumber(value: Double, decimals: Int = 1): String = NumberFormat.getNumberInstance(FRENCH).apply {
    maximumFractionDigits = decimals
    minimumFractionDigits = 0
}.format(value)

/** Multiplicateur de dégâts en pourcentage → « ×2 », « ×½ », « ×¼ », « ×0 ». */
fun formatFactor(percent: Int): String = when (percent) {
    25 -> "×¼"
    50 -> "×½"
    else -> "×" + formatNumber(percent / 100.0, decimals = 2)
}
