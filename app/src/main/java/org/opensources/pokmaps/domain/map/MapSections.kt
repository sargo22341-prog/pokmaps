package org.opensources.pokmaps.domain.map

/** Un badge par niveau affichable ; les salles du même niveau sont déjà réunies dans ses tuiles. */
internal object MapSections {
    fun build(maps: Map<Int, MapInfo>): Map<Int, List<MapFloor>> {
        val buildings = maps.values.filter { it.isDisplayable && !it.isWorld }
            .mapNotNull { map ->
                FloorLevel.parse(map.identifier)?.let { (building, level) ->
                    building to MapFloor(map.id, level, map.name)
                }
            }.groupBy({ it.first }, { it.second })
            .values.filter { it.size > 1 }
        return buildings.flatMap { floors ->
            val sorted = floors.sortedByDescending { it.level.order }
            sorted.map { it.mapId to sorted }
        }.toMap()
    }
}
