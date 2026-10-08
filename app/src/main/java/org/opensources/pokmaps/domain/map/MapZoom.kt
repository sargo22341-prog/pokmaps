package org.opensources.pokmaps.domain.map

import kotlin.math.min

/**
 * Zoom minimal des cartes du monde et des niveaux assemblés : un peu plus loin que la carte entière, pour qu'un lieu au bord
 * (le Plateau Indigo à l'ouest de Kanto) puisse être amené vers le centre, avec une marge autour de la carte.
 */
object MapZoom {
    /** Taille de la carte, au zoom minimal, par rapport à la carte qui tient tout juste dans la vue. */
    const val ZOOM_OUT = 0.75

    /** Zoom minimal pour une vue et une carte en pixels, null tant que la vue n'a pas de taille. */
    fun minScale(viewWidth: Int, viewHeight: Int, mapWidth: Int, mapHeight: Int): Double? {
        if (viewWidth <= 0 || viewHeight <= 0) return null
        require(mapWidth > 0 && mapHeight > 0) { "Carte vide : $mapWidth × $mapHeight" }
        val fit = min(viewWidth.toDouble() / mapWidth, viewHeight.toDouble() / mapHeight)
        return fit * ZOOM_OUT
    }
}
