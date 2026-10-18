package org.opensources.pokmaps.domain.map

/** Rectangle visible, normalisé dans l'image complète de la carte. */
data class MapFrame(val left: Double, val top: Double, val right: Double, val bottom: Double) {
    init {
        require(left >= 0.0 && top >= 0.0 && right <= 1.0 && bottom <= 1.0)
        require(left < right && top < bottom)
    }

    companion object {
        val FULL = MapFrame(0.0, 0.0, 1.0, 1.0)
    }
}
