package org.opensources.pokmaps.domain.map

/** Niveaux géographiques déjà assemblés dans les assets, indépendants des étages numérotés. */
internal object MapLandscape {
    private val groups = listOf(
        listOf(
            "shoal-cave-high-tide-1f-plan" to FloorLevel.Landscape.HIGH_TIDE,
            "shoal-cave-low-tide-1f-plan" to FloorLevel.Landscape.LOW_TIDE,
            "shoal-cave-low-tide-b1f-plan" to FloorLevel.Landscape.LOW_TIDE_BASEMENT
        )
    )

    fun floors(maps: Map<Int, MapInfo>): Map<Int, List<MapFloor>> = groups.flatMap { group ->
        val floors = group.mapNotNull { (identifier, level) ->
            maps.values.firstOrNull { it.identifier == identifier && it.isDisplayable }
                ?.let { MapFloor(it.id, level, it.name) }
        }
        if (floors.size < 2) emptyList() else floors.map { it.mapId to floors }
    }.toMap() + divingFloors(maps)

    private fun divingFloors(maps: Map<Int, MapInfo>): Map<Int, List<MapFloor>> {
        val surface = maps.values.firstOrNull { it.identifier == "hoenn" } ?: return emptyMap()
        val underwater = maps.values.firstOrNull { it.identifier == "hoenn-underwater" } ?: return emptyMap()
        val routes = maps.values.filter { it.parentId == surface.id }
        val paired = maps.values.filter { it.parentId == underwater.id }.flatMap { depth ->
            val route = routes.firstOrNull {
                it.x == depth.x && it.y == depth.y && it.width == depth.width && it.height == depth.height
            } ?: return@flatMap emptyList()
            val floors = diveLevels(route, depth)
            listOf(route.id to floors, depth.id to floors)
        }.toMap()
        val route = routes.firstOrNull { it.identifier == "route134" } ?: return paired
        val depth = maps.values.firstOrNull { it.identifier == "underwater-route134" && it.isDisplayable }
            ?: return paired
        val floors = diveLevels(route, depth)
        return paired + mapOf(route.id to floors, depth.id to floors)
    }

    private fun diveLevels(route: MapInfo, depth: MapInfo): List<MapFloor> = listOf(
        MapFloor(route.id, FloorLevel.Landscape.SURFACE, route.name),
        MapFloor(depth.id, FloorLevel.Landscape.UNDERWATER, depth.name)
    )
}
