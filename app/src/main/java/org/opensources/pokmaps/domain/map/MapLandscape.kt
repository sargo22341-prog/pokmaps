package org.opensources.pokmaps.domain.map

/** Niveaux géographiques déjà assemblés dans les assets, indépendants des étages numérotés. */
internal object MapLandscape {
    private val groups = listOf(
        listOf("hoenn" to FloorLevel.Landscape.SURFACE, "hoenn-underwater" to FloorLevel.Landscape.UNDERWATER),
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
    }.toMap()
}
