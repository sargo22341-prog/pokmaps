package org.opensources.pokmaps.domain.map

/** Plans superposés d'une même carte DS ; les suffixes viennent du générateur de tuiles. */
internal object MapLevels {
    fun build(maps: Map<Int, MapInfo>): Map<Int, List<MapFloor>> {
        val groups = maps.values.filter { it.isDisplayable }.mapNotNull { map ->
            val match = LOWER.matchEntire(map.identifier) ?: return@mapNotNull null
            val (base, number) = match.destructured
            val depth = number.ifEmpty { "1" }.toInt()
            base to MapFloor(map.id, FloorLevel.Height(depth), map.name)
        }.groupBy({ it.first }, { it.second })
        return groups.flatMap { (identifier, lower) ->
            val upper = maps.values.firstOrNull { it.identifier == identifier && it.isDisplayable }
                ?: error("Plan supérieur absent : $identifier")
            val levels = listOf(MapFloor(upper.id, FloorLevel.Height(0), upper.name)) +
                lower.sortedByDescending { it.level.order }
            levels.map { it.mapId to levels }
        }.toMap()
    }

    private val LOWER = Regex("^(.+)-lower(?:-([1-9][0-9]*))?$")
}
