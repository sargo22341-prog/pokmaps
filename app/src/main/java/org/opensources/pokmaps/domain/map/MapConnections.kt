package org.opensources.pokmaps.domain.map

import kotlin.math.abs
import kotlin.math.hypot

/** Liaison entre deux zones affichées ensemble, du milieu d'un passage au milieu de son arrivée. */
data class MapConnection(
    val warpId: Int,
    val x: Int,
    val y: Int,
    val targetX: Int,
    val targetY: Int,
    val warpIds: Set<Int> = setOf(warpId)
)

internal object MapConnections {
    /** Case d'un passage et case d'arrivée, toutes deux connues. */
    private data class Step(val id: Int, val x: Int, val y: Int, val targetX: Int, val targetY: Int)

    fun build(catalog: MapCatalog, mapId: Int): List<MapConnection> {
        if (catalog.isWorld(mapId)) return emptyList()
        val passages = mutableListOf<MutableList<Step>>()
        for (warp in catalog.partsOf(mapId).flatMap { catalog.warps[it].orEmpty() }) {
            val targetId = warp.targetMapId ?: continue
            if (targetId == warp.mapId || catalog.displayedMapOf(targetId)?.id != mapId) continue
            val step = Step(warp.id, warp.x, warp.y, warp.targetX ?: continue, warp.targetY ?: continue)
            // Une porte large a une case par passage : chacune rejoint le passage d'une case voisine, dans les deux
            // sens, même au-delà de deux cases (les portes du Parc Safari en ont trois).
            val passage = passages.firstOrNull { members -> members.any { samePassage(it, step) } }
            if (passage == null) passages += mutableListOf(step) else passage += step
        }
        return passages.map(::connection)
    }

    /** Trait du milieu des cases d'un bout au milieu des cases de l'autre, quel que soit le sens de chaque case. */
    private fun connection(members: List<Step>): MapConnection {
        val first = members.first()
        val starts = mutableSetOf<Pair<Int, Int>>()
        val ends = mutableSetOf<Pair<Int, Int>>()
        for (step in members) {
            val forward = hypot((step.x - first.x).toDouble(), (step.y - first.y).toDouble()) <=
                hypot((step.targetX - first.x).toDouble(), (step.targetY - first.y).toDouble())
            starts += if (forward) step.x to step.y else step.targetX to step.targetY
            ends += if (forward) step.targetX to step.targetY else step.x to step.y
        }
        return MapConnection(
            first.id,
            starts.sumOf { it.first } / starts.size,
            starts.sumOf { it.second } / starts.size,
            ends.sumOf { it.first } / ends.size,
            ends.sumOf { it.second } / ends.size,
            members.map { it.id }.toSet()
        )
    }

    private fun samePassage(first: Step, second: Step): Boolean = (
        near(first.x, first.y, second.x, second.y) && near(first.targetX, first.targetY, second.targetX, second.targetY)
        ) ||
        (
            near(first.x, first.y, second.targetX, second.targetY) &&
                near(first.targetX, first.targetY, second.x, second.y)
            )

    private fun near(x: Int, y: Int, tx: Int, ty: Int): Boolean = abs(x - tx) <= 16 && abs(y - ty) <= 16
}
