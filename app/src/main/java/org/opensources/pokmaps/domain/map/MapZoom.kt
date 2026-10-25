package org.opensources.pokmaps.domain.map

import kotlin.math.min
import org.opensources.pokmaps.domain.model.GameMap

/**
 * Zoom minimal des mondes et plans assemblés, avec une marge autour de la carte entière.
 * Le monde commun HGSS garde une limite plus proche pour préserver la fluidité des repères.
 */
object MapZoom {
    /** Taille de la carte, au zoom minimal, par rapport à la carte qui tient tout juste dans la vue. */
    const val ZOOM_OUT = 0.75

    /** Le monde HGSS commun doit limiter le nombre de repères dans la fenêtre, même après une rotation. */
    fun worldMinimumScale(map: GameMap): Double? =
        if (map.isWorld && map.versionGroupIdentifier == "heartgold-soulsilver") MIN_HGSS_WORLD_SCALE else null

    fun minScale(viewWidth: Int, viewHeight: Int, map: GameMap): Double? =
        minScale(viewWidth, viewHeight, map.width, map.height)?.coerceAtLeast(worldMinimumScale(map) ?: 0.0)

    /** Zoom minimal pour une vue et une carte en pixels, null tant que la vue n'a pas de taille. */
    fun minScale(viewWidth: Int, viewHeight: Int, mapWidth: Int, mapHeight: Int): Double? {
        if (viewWidth <= 0 || viewHeight <= 0) return null
        require(mapWidth > 0 && mapHeight > 0) { "Carte vide : $mapWidth × $mapHeight" }
        val fit = min(viewWidth.toDouble() / mapWidth, viewHeight.toDouble() / mapHeight)
        return fit * ZOOM_OUT
    }

    private const val MIN_HGSS_WORLD_SCALE = 0.5
}
