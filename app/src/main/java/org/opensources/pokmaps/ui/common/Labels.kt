package org.opensources.pokmaps.ui.common

import androidx.annotation.StringRes
import java.text.NumberFormat
import java.util.Locale
import org.opensources.pokmaps.R
import org.opensources.pokmaps.domain.model.ObtainMethod
import org.opensources.pokmaps.domain.pokemon.DamageClass

@get:StringRes
val ObtainMethod.label: Int
    get() = when (this) {
        ObtainMethod.WALK -> R.string.method_walk
        ObtainMethod.FISHING -> R.string.method_fishing
        ObtainMethod.SURF -> R.string.method_surf
        ObtainMethod.GIFT -> R.string.method_gift
        ObtainMethod.STATIC -> R.string.method_static
        ObtainMethod.TRADE -> R.string.method_trade
        ObtainMethod.EVOLUTION -> R.string.method_evolution
    }

@get:StringRes
val DamageClass.label: Int
    get() = when (this) {
        DamageClass.PHYSICAL -> R.string.damage_physical
        DamageClass.SPECIAL -> R.string.damage_special
        DamageClass.STATUS -> R.string.status_label
    }

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
