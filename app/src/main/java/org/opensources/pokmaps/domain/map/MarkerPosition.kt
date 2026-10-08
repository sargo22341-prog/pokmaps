package org.opensources.pokmaps.domain.map

import kotlin.math.roundToInt

/** Point où dessiner un marqueur, en pixels de la carte affichée. */
data class MarkerPosition(val x: Int, val y: Int)

/** Largeur, dans une case de 16 px, sur laquelle s'écartent les objets qui la partagent. */
private const val SHARED_CELL_SPAN_PX = 10

/** Objets d'une même case, écartés côte à côte et centrés sur la case ; un objet seul reste au centre. */
internal fun spreadInCell(shared: List<MapObject>): List<Pair<Int, MarkerPosition>> {
    if (shared.size == 1) return listOf(shared.single().let { it.id to MarkerPosition(it.x, it.y) })
    val step = SHARED_CELL_SPAN_PX.toFloat() / (shared.size - 1)
    return shared.mapIndexed { index, obj ->
        obj.id to MarkerPosition(obj.x + (index * step - SHARED_CELL_SPAN_PX / 2f).roundToInt(), obj.y)
    }
}
