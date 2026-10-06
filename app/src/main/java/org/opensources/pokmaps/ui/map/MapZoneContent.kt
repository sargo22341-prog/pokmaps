package org.opensources.pokmaps.ui.map

import org.opensources.pokmaps.domain.map.MapCatalog
import org.opensources.pokmaps.domain.map.MapInfo
import org.opensources.pokmaps.domain.map.SpotKind
import org.opensources.pokmaps.domain.map.WildPlacement
import org.opensources.pokmaps.domain.model.Encounter

internal object MapZoneContent {
    /** Lieux accessibles depuis une ville, une route ou une carte intérieure (bâtiments, grottes, étages, sorties). */
    fun places(catalog: MapCatalog, zone: MapInfo): List<MapPlace> =
        catalog.accessibleFrom(zone.id).mapNotNull { warp ->
            val target = warp.targetMapId?.let { catalog.maps[it] } ?: return@mapNotNull null
            MapPlace(target.id, target.name, warp.targetX, warp.targetY)
        }

    /**
     * Dessine les Pokémon sauvages du lieu sur leur terrain : herbes (ou sol des grottes) en marchant, eau en surfant
     * ou en pêchant. Chacun apparaît au moins une fois (les plus fréquents parfois deux), à des emplacements bien
     * répartis sur le terrain ; sur un terrain étroit, ils sont rangés côte à côte, plus petits.
     */
    fun wildMarkers(catalog: MapCatalog, zone: MapInfo, encounters: List<Encounter>): List<WildMarker> {
        val spots = catalog.spots[zone.id].orEmpty().groupBy { it.kind }
        // Objets, personnages et entrées gardent leur place : pas de Pokémon dessiné juste à côté.
        val displayed = catalog.displayedMapOf(zone.id)?.id ?: zone.id
        val obstacles = catalog.partsOf(displayed).flatMap { catalog.objects[it].orEmpty() }.map { it.x to it.y } +
            catalog.entrancesOf(displayed).map { it.x to it.y }
        val wild = encounters.mapNotNull { e -> WildMethod.from(e.method)?.let { it to e } }
        // Surf et pêche partagent l'eau : ils sont répartis ensemble pour ne pas se superposer.
        return wild.groupBy { (method, _) -> method == WildMethod.WALK }.flatMap { (walking, list) ->
            val terrain = if (walking) spots[SpotKind.GRASS] ?: spots[SpotKind.FLOOR] else spots[SpotKind.WATER]
            val species = list.groupBy { (method, e) -> method to e.pokemonId }.map { (key, group) ->
                val encounter = group.first().second
                WildMarker(encounter.pokemonId, encounter.pokemonName, key.first, 0, 0) to
                    group.sumOf { it.second.chance ?: 0.0 }
            }.sortedByDescending { it.second }
            WildPlacement.place(
                items = species.map { it.first },
                weights = species.map { it.second },
                spots = WildPlacement.awayFrom(terrain.orEmpty().map { it.x to it.y }, obstacles, species.size),
                fallback = zone.centerInDisplay(),
                seed = zone.id * 2 + if (walking) 0 else 1
            ).map { it.item.copy(x = it.x, y = it.y, scale = it.scale) }
        }
    }

    private fun MapInfo.centerInDisplay(): Pair<Int, Int> =
        if (parentId == null) width / 2 to height / 2 else x + width / 2 to y + height / 2
}
