package org.opensources.pokmaps.domain.map

import kotlin.math.abs

/** Liaison entre deux zones affichées ensemble, avec les coordonnées exactes de leurs passages. */
data class MapConnection(val warpId: Int, val x: Int, val y: Int, val targetX: Int, val targetY: Int)

internal object MapConnections {
    fun build(catalog: MapCatalog, mapId: Int): List<MapConnection> {
        if (catalog.isWorld(mapId)) return emptyList()
        val connections = mutableListOf<MapConnection>()
        for (warp in catalog.partsOf(mapId).flatMap { catalog.warps[it].orEmpty() }) {
            val targetId = warp.targetMapId ?: continue
            if (targetId == warp.mapId || catalog.displayedMapOf(targetId)?.id != mapId) continue
            val tx = warp.targetX ?: continue
            val ty = warp.targetY ?: continue
            val connection = MapConnection(warp.id, warp.x, warp.y, tx, ty)
            if (connections.none { samePassage(it, connection) }) connections += connection
        }
        return connections
    }

    private fun samePassage(first: MapConnection, second: MapConnection): Boolean = (
        near(first.x, first.y, second.x, second.y) &&
            near(first.targetX, first.targetY, second.targetX, second.targetY)
        ) ||
        (
            near(first.x, first.y, second.targetX, second.targetY) &&
                near(first.targetX, first.targetY, second.x, second.y)
            )

    private fun near(x: Int, y: Int, tx: Int, ty: Int): Boolean = abs(x - tx) <= 16 && abs(y - ty) <= 16
}
