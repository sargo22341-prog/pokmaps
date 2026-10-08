package org.opensources.pokmaps.ui.map

import androidx.compose.ui.graphics.Color

internal fun passageColor(index: Int): Color {
    if (index < 0) return Color(0xFF2962FF)
    // Le pas d'or espace les teintes successives sans recycler une petite palette.
    return Color.hsv((index * 137.508f) % 360f, 0.85f, 0.9f)
}
